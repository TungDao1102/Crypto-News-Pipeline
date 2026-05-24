import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from src.ai_handler import (
    AIConsumer,
    AllModelsExhausted,
    OpenRouterClient,
    PROMPT_REGISTRY,
    TextPreprocessor,
    TokenBucket,
    TranslatedText,
    prompt_for_tags,
)
from src.models import DraftContent


# ─── Model Tests ─────────────────────────────────────────────────

class TestDraftContentModel:
    def test_construct_with_required_fields(self):
        d = DraftContent(
            title_vn="tiêu đề",
            telegram_markdown="nội dung tg",
            binance_square_markdown="nội dung binance",
        )
        assert d.title_vn == "tiêu đề"
        assert d.telegram_markdown == "nội dung tg"
        assert d.binance_square_markdown == "nội dung binance"

    def test_status_defaults_to_pending(self):
        d = DraftContent(
            title_vn="a", telegram_markdown="b", binance_square_markdown="c"
        )
        assert d.status == "pending"

    def test_tags_defaults_to_empty(self):
        d = DraftContent(
            title_vn="a", telegram_markdown="b", binance_square_markdown="c"
        )
        assert d.tags == []

    def test_used_fallback_defaults_to_false(self):
        d = DraftContent(
            title_vn="a", telegram_markdown="b", binance_square_markdown="c"
        )
        assert d.used_fallback is False

    def test_status_literal_values(self):
        d = DraftContent(
            title_vn="a", telegram_markdown="b", binance_square_markdown="c"
        )
        for status in ("pending", "approved", "rejected", "published"):
            d.status = status
            assert d.status == status


# ─── TextPreprocessor Tests ──────────────────────────────────────

class TestTextPreprocessor:
    def setup_method(self):
        self.pre = TextPreprocessor()

    def test_emoji_in_range_stripped(self):
        # U+1F600 is in [\U0001F000-\U0010FFFF], removed + whitespace collapsed
        result = self.pre.preprocess("Hello \U0001F600 world")
        assert "\U0001F600" not in result

    def test_rocket_emoji_stripped(self):
        # 🚀 is U+1F680, in [\U0001F000-\U0010FFFF] range
        result = self.pre.preprocess("Hello \U0001F680 world")
        assert "\U0001F680" not in result

    def test_emoji_outside_range_not_stripped(self):
        # ✅ is U+2705, outside [\U0001F000-\U0010FFFF]
        assert "\u2705" in self.pre.preprocess("\u2705 test")

    def test_contract_address_preserved(self):
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        result = self.pre.preprocess(f"Contract: {addr}")
        assert addr in result

    def test_code_block_preserved(self):
        result = self.pre.preprocess("```\nx = 1\n```outside")
        assert "x = 1" in result

    def test_whitespace_normalized(self):
        assert self.pre.preprocess("  too   many   spaces  ") == "too many spaces"

    def test_urls_preserved(self):
        url = "https://example.com/airdrop?ref=test"
        result = self.pre.preprocess(f"Check {url} now")
        assert url in result

    def test_multiline_normalized(self):
        result = self.pre.preprocess("line1\n\n\nline2")
        assert result == "line1 line2"

    def test_mixed_protection_and_emoji(self):
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        result = self.pre.preprocess(f"\U0001F680 Send to {addr}")
        assert addr in result
        assert "\U0001F680" not in result

    def test_empty_string(self):
        assert self.pre.preprocess("") == ""

    def test_only_whitespace(self):
        assert self.pre.preprocess("   \n\n  ") == ""


# ─── TokenBucket Tests ───────────────────────────────────────────

class TestTokenBucket:
    def test_initial_tokens_at_capacity(self):
        tb = TokenBucket(capacity=5, refill_rate=10)
        assert tb.tokens == 5.0

    @pytest.mark.asyncio
    async def test_allows_immediate_acquire_up_to_capacity(self):
        tb = TokenBucket(capacity=5, refill_rate=10)
        for _ in range(5):
            await tb.acquire()
        assert tb.tokens == pytest.approx(0.0, abs=1e-3)

    @pytest.mark.asyncio
    async def test_blocks_when_exhausted(self):
        tb = TokenBucket(capacity=1, refill_rate=0.01)
        await tb.acquire()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(tb.acquire(), timeout=0.05)

    @pytest.mark.asyncio
    async def test_acquire_multiple_deducts_correctly(self):
        tb = TokenBucket(capacity=10, refill_rate=1000)
        await tb.acquire(tokens=4)
        assert tb.tokens == pytest.approx(6.0, abs=1e-2)
        await tb.acquire(tokens=4)
        assert tb.tokens == pytest.approx(2.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_capacity_not_exceeded_after_refill(self):
        tb = TokenBucket(capacity=10, refill_rate=1)
        await tb.acquire(tokens=10)
        assert tb.tokens == pytest.approx(0.0, abs=1e-3)
        await asyncio.sleep(0.05)
        tb._refill()
        assert tb.tokens <= 10.0

    def test_refill_respects_capacity(self):
        tb = TokenBucket(capacity=5, refill_rate=100)
        tb.tokens = 0.0
        tb._last_refill -= 10
        tb._refill()
        assert tb.tokens == 5.0


# ─── PROMPT_REGISTRY Tests ───────────────────────────────────────

class TestPromptRegistry:
    def test_has_five_entries(self):
        assert len(PROMPT_REGISTRY) == 5

    def test_has_required_keys(self):
        for key in ("default", "airdrop", "testnet", "macro", "defi"):
            assert key in PROMPT_REGISTRY

    def test_each_entry_has_three_fields(self):
        for key, entry in PROMPT_REGISTRY.items():
            assert "translate_system" in entry
            assert "rewrite_system" in entry
            assert "user_template" in entry

    def test_each_entry_has_non_empty_prompts(self):
        for key, entry in PROMPT_REGISTRY.items():
            assert len(entry["translate_system"]) > 50
            assert len(entry["rewrite_system"]) > 50
            assert len(entry["user_template"]) > 10

    def test_user_template_has_placeholder(self):
        for key, entry in PROMPT_REGISTRY.items():
            assert "{raw_text}" in entry["user_template"]


class TestPromptForTags:
    def test_airdrop_priority(self):
        result = prompt_for_tags(["airdrop"])
        assert result is PROMPT_REGISTRY["airdrop"]

    def test_priority_order(self):
        result = prompt_for_tags(["testnet", "airdrop"])
        assert result is PROMPT_REGISTRY["airdrop"]

    def test_falls_back_to_default(self):
        result = prompt_for_tags(["unknown"])
        assert result is PROMPT_REGISTRY["default"]

    def test_empty_tags_returns_default(self):
        result = prompt_for_tags([])
        assert result is PROMPT_REGISTRY["default"]

    def test_defi_selected_when_no_higher_priority(self):
        result = prompt_for_tags(["defi"])
        assert result is PROMPT_REGISTRY["defi"]


# ─── OpenRouterClient Tests ──────────────────────────────────────

class TestOpenRouterClient:
    def test_init_stores_dependencies(self):
        client = httpx.AsyncClient()
        orc = OpenRouterClient(api_key="sk-test", http_client=client)
        assert orc.api_key == "sk-test"
        assert orc.http_client is client

    @pytest.mark.asyncio
    async def test_call_sends_correct_request(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
        mock_client.post = AsyncMock(return_value=mock_response)

        orc = OpenRouterClient(api_key="sk-test", http_client=mock_client)
        result = await orc.call(
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result["choices"][0]["message"]["content"] == "hello"
        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["model"] == "test-model"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-test"

    @pytest.mark.asyncio
    async def test_call_with_fallback_tries_models_in_order(self):
        fail_response = MagicMock()
        fail_response.raise_for_status.side_effect = httpx.TimeoutException("timeout")
        ok_response = MagicMock()
        ok_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=[fail_response, ok_response])

        orc = OpenRouterClient(api_key="sk-test", http_client=mock_client)
        result = await orc.call_with_fallback(
            system_prompt="be helpful",
            user_content="hello",
        )
        assert result["choices"][0]["message"]["content"] == "ok"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_all_models_exhausted_raises_exception(self):
        fail = MagicMock()
        fail.raise_for_status.side_effect = httpx.TimeoutException("timeout")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=fail)

        orc = OpenRouterClient(api_key="sk-test", http_client=mock_client)
        with pytest.raises(AllModelsExhausted):
            await orc.call_with_fallback(
                system_prompt="be helpful",
                user_content="hello",
            )

    @pytest.mark.asyncio
    async def test_call_structured_returns_tuple(self):
        raw = '{"translated_text": "xin chào"}'
        ok_response = MagicMock()
        ok_response.json.return_value = {"choices": [{"message": {"content": raw}}]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=ok_response)

        orc = OpenRouterClient(api_key="sk-test", http_client=mock_client)
        result, used_fallback = await orc.call_structured(
            system_prompt="translate",
            user_content="hello",
            response_model=TranslatedText,
        )
        assert isinstance(result, TranslatedText)
        assert result.translated_text == "xin chào"
        assert used_fallback is False

    @pytest.mark.asyncio
    async def test_call_structured_fallback_flag_true(self):
        fail = MagicMock()
        fail.raise_for_status.side_effect = httpx.TimeoutException("timeout")
        raw = '{"translated_text": "xin chào"}'
        ok = MagicMock()
        ok.json.return_value = {"choices": [{"message": {"content": raw}}]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=[fail, ok])

        orc = OpenRouterClient(api_key="sk-test", http_client=mock_client)
        _, used_fallback = await orc.call_structured(
            system_prompt="translate",
            user_content="hello",
            response_model=TranslatedText,
        )
        assert used_fallback is True

    @pytest.mark.asyncio
    async def test_call_structured_sends_json_object_response_format(self):
        raw = '{"translated_text": "hi"}'
        ok_response = MagicMock()
        ok_response.json.return_value = {"choices": [{"message": {"content": raw}}]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=ok_response)

        orc = OpenRouterClient(api_key="sk-test", http_client=mock_client)
        await orc.call_structured(
            system_prompt="x",
            user_content="y",
            response_model=TranslatedText,
        )
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["response_format"] == {"type": "json_object"}


# ─── AIConsumer Tests ────────────────────────────────────────────

class TestAIConsumer:
    def make_consumer(self, **kwargs):
        defaults = dict(
            raw_queue=asyncio.Queue(),
            result_queue=asyncio.Queue(),
            channel_tags={"@channel": ["airdrop"]},
            rate_limiter=TokenBucket(capacity=100, refill_rate=1000),
            http_client=None,
            api_key="test",
            worker_count=2,
        )
        defaults.update(kwargs)
        return AIConsumer(**defaults)

    @pytest.mark.asyncio
    async def test_shutdown_cancels_workers(self):
        consumer = self.make_consumer()
        consumer._workers = [
            asyncio.create_task(asyncio.Event().wait()),
            asyncio.create_task(asyncio.Event().wait()),
        ]
        await asyncio.sleep(0.01)
        await consumer.shutdown()
        assert all(w.done() or w.cancelled() for w in consumer._workers)

    @pytest.mark.asyncio
    async def test_pause_cooldown(self):
        consumer = self.make_consumer()
        assert not consumer._pause.is_set()
        await consumer.pause_ai(duration=0.1)
        assert consumer._pause.is_set()
        await asyncio.sleep(0.2)
        assert not consumer._pause.is_set()

    @pytest.mark.asyncio
    async def test_pause_cancels_previous(self):
        consumer = self.make_consumer()
        await consumer.pause_ai(duration=10)
        first_task = consumer._pause_cooldown_task
        await consumer.pause_ai(duration=0.1)
        await asyncio.sleep(0)
        assert first_task.done() or first_task.cancelled()
        await asyncio.sleep(0.2)
        assert not consumer._pause.is_set()

    @pytest.mark.asyncio
    async def test_worker_respects_pause(self):
        consumer = self.make_consumer()
        await consumer.pause_ai(duration=0.1)
        assert consumer._pause.is_set()

    @pytest.mark.asyncio
    async def test_process_message_full_success(self):
        consumer = self.make_consumer()
        msg = MagicMock(source_channel="@channel", raw_text="Bitcoin hits $100k")
        with (
            patch.object(consumer._preprocessor, "preprocess", return_value="Bitcoin hits $100k"),
            patch.object(consumer._openrouter, "call_structured", new=AsyncMock(
                side_effect=[
                    (TranslatedText(translated_text="Bitcoin đạt $100k"), False),
                    (DraftContent(
                        title_vn="Bitcoin đạt $100k",
                        telegram_markdown="Bitcoin đạt $100k",
                        binance_square_markdown="Bitcoin đạt $100k",
                    ), False),
                ]
            )),
        ):
            result = await consumer._process_message(msg)
        assert result is not None
        assert result.title_vn == "Bitcoin đạt $100k"
        assert result.status == "pending"
        assert result.tags == ["airdrop"]
        assert result.used_fallback is False

    @pytest.mark.asyncio
    async def test_process_message_partial_failure(self):
        consumer = self.make_consumer()
        msg = MagicMock(source_channel="@channel", raw_text="Ethereum upgrade")
        with (
            patch.object(consumer._preprocessor, "preprocess", return_value="Ethereum upgrade"),
            patch.object(consumer._openrouter, "call_structured", new=AsyncMock(
                side_effect=[
                    (TranslatedText(translated_text="Ethereum nâng cấp"), False),
                    AllModelsExhausted("all failed"),
                ]
            )),
        ):
            result = await consumer._process_message(msg)
        assert result is not None
        assert "Ethereum" in result.telegram_markdown
        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_process_message_full_failure_translate(self):
        consumer = self.make_consumer()
        msg = MagicMock(source_channel="@channel", raw_text="Crypto news")
        with (
            patch.object(consumer._preprocessor, "preprocess", return_value="Crypto news"),
            patch.object(consumer._openrouter, "call_structured", new=AsyncMock(
                side_effect=AllModelsExhausted("all failed"),
            )),
        ):
            result = await consumer._process_message(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_message_empty_after_preprocess(self):
        consumer = self.make_consumer()
        msg = MagicMock(source_channel="@channel", raw_text="   ")
        with patch.object(consumer._preprocessor, "preprocess", return_value=""):
            result = await consumer._process_message(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_channel_tags_lookup(self):
        consumer = self.make_consumer(channel_tags={"@source_a": ["airdrop"]})
        msg = MagicMock(source_channel="@source_a", raw_text="hello world")
        with (
            patch.object(consumer._preprocessor, "preprocess", return_value="hello world"),
            patch.object(consumer._openrouter, "call_structured", new=AsyncMock(
                side_effect=[
                    (TranslatedText(translated_text="xin chào"), False),
                    (DraftContent(
                        title_vn="xin chào",
                        telegram_markdown="xin chào",
                        binance_square_markdown="xin chào",
                    ), False),
                ]
            )),
        ):
            result = await consumer._process_message(msg)
        assert result is not None
        assert result.tags == ["airdrop"]

    @pytest.mark.asyncio
    async def test_unknown_channel_falls_to_default_prompt(self):
        consumer = self.make_consumer()
        msg = MagicMock(source_channel="@unknown", raw_text="test")
        with (
            patch.object(consumer._preprocessor, "preprocess", return_value="test"),
            patch.object(consumer._openrouter, "call_structured", new=AsyncMock(
                side_effect=[
                    (TranslatedText(translated_text="kiểm tra"), False),
                    (DraftContent(
                        title_vn="kiểm tra",
                        telegram_markdown="kiểm tra",
                        binance_square_markdown="kiểm tra",
                    ), False),
                ]
            )),
        ):
            result = await consumer._process_message(msg)
        assert result is not None
        assert result.tags == []


# ─── Cooldown / AllModelsExhausted Integration ───────────────────

@pytest.mark.asyncio
async def test_pause_cooldown():
    from src.ai_handler import AIConsumer

    consumer = AIConsumer(
        raw_queue=asyncio.Queue(),
        result_queue=asyncio.Queue(),
        channel_tags={},
        rate_limiter=None,
        http_client=None,
        api_key="test",
    )
    assert not consumer._pause.is_set()
    await consumer.pause_ai(duration=0.1)
    assert consumer._pause.is_set()
    await asyncio.sleep(0.2)
    assert not consumer._pause.is_set()


@pytest.mark.asyncio
async def test_pause_cancels_previous():
    from src.ai_handler import AIConsumer

    consumer = AIConsumer(
        raw_queue=asyncio.Queue(),
        result_queue=asyncio.Queue(),
        channel_tags={},
        rate_limiter=None,
        http_client=None,
        api_key="test",
    )
    await consumer.pause_ai(duration=10)
    first_task = consumer._pause_cooldown_task
    await consumer.pause_ai(duration=0.1)
    await asyncio.sleep(0)
    assert first_task.done() or first_task.cancelled()
    await asyncio.sleep(0.2)
    assert not consumer._pause.is_set()


@pytest.mark.asyncio
async def test_worker_respects_pause():
    from src.ai_handler import AIConsumer

    consumer = AIConsumer(
        raw_queue=asyncio.Queue(),
        result_queue=asyncio.Queue(),
        channel_tags={},
        rate_limiter=None,
        http_client=None,
        api_key="test",
    )
    await consumer.pause_ai(duration=0.1)
    assert consumer._pause.is_set()
