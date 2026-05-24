from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from src.models import PublishResult
from src.publisher.base import BasePublisher, PublisherResult
from src.publisher.binance_square import BinanceSquareClient, BinanceSquarePublisher, strip_markdown
from src.publisher.consumer import PublisherConsumer
from src.publisher.tag_injector import TagInjector
from src.publisher.telegram import TelegramPublisher


class TestPublisherResultDataclass:

    def test_construct_with_required(self):
        result = PublisherResult(platform="telegram", success=True)
        assert result.platform == "telegram"
        assert result.success is True
        assert result.url is None
        assert result.error is None

    def test_construct_with_all_fields(self):
        result = PublisherResult(
            platform="binance_square",
            success=False,
            url="https://example.com",
            error="Something went wrong",
        )
        assert result.platform == "binance_square"
        assert result.success is False
        assert result.url == "https://example.com"
        assert result.error == "Something went wrong"


class TestBasePublisher:

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BasePublisher()

    def test_concrete_subclass_must_implement_abstract_methods(self):
        class Incomplete(BasePublisher):
            pass
        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_works(self):
        class Concrete(BasePublisher):
            async def publish(self, content):
                return PublisherResult(platform="test", success=True)
            async def close(self):
                pass

        instance = Concrete()
        assert isinstance(instance, BasePublisher)


class TestPublishResultPydanticModel:

    def test_construct_with_required(self):
        result = PublishResult(platform="telegram", success=True)
        assert result.platform == "telegram"
        assert result.success is True
        assert result.url is None
        assert result.error is None
        assert result.post_id is None

    def test_construct_with_all_fields(self):
        result = PublishResult(
            platform="binance_square",
            success=False,
            url="https://example.com",
            error="fail",
            post_id="123",
        )
        assert result.platform == "binance_square"
        assert result.success is False
        assert result.url == "https://example.com"
        assert result.error == "fail"
        assert result.post_id == "123"

    def test_invalid_platform_raises(self):
        with pytest.raises(ValidationError):
            PublishResult(platform="invalid", success=True)

    def test_invalid_success_type_raises(self):
        with pytest.raises(ValidationError):
            PublishResult(platform="telegram", success=[1, 2])


class TestTagInjectorStripTags:

    def test_strips_simple_tag_block(self):
        injector = TagInjector()
        content = "Some content\n\n#Airdrop #DeFi $BTC\nMore content"
        result = injector.strip_tags(content)
        assert "#Airdrop" not in result
        assert "#DeFi" not in result
        assert "$BTC" not in result
        assert "Some content" in result
        assert "More content" in result

    def test_preserves_single_hash_in_text(self):
        injector = TagInjector()
        content = "Topic #1 is important"
        result = injector.strip_tags(content)
        assert "Topic #1" in result

    def test_preserves_non_tag_lines(self):
        injector = TagInjector()
        content = "Hello world\nSome text here\nFinal line"
        result = injector.strip_tags(content)
        assert result == "Hello world\nSome text here\nFinal line"

    def test_strips_only_tag_line_not_adjacent_text(self):
        injector = TagInjector()
        content = "#Airdrop #DeFi\nBut this is actual content"
        result = injector.strip_tags(content)
        assert "#Airdrop #DeFi" not in result
        assert "But this is actual content" in result


class TestTagInjectorSelectCashtags:

    def test_selects_matching_cashtags_in_priority_order(self):
        injector = TagInjector()
        result = injector.select_cashtags(["btc", "eth", "sol"])
        assert result == ["$BTC", "$ETH", "$SOL"]

    def test_caps_at_three(self):
        injector = TagInjector()
        result = injector.select_cashtags(["btc", "eth", "sol", "arb", "op"])
        assert len(result) == 3

    def test_returns_empty_when_no_match(self):
        injector = TagInjector()
        result = injector.select_cashtags(["xyz", "unknown"])
        assert result == []

    def test_case_insensitive_matching(self):
        injector = TagInjector()
        result = injector.select_cashtags(["BTC", "Eth", "SoL"])
        assert result == ["$BTC", "$ETH", "$SOL"]

    def test_returns_empty_for_empty_tags(self):
        injector = TagInjector()
        result = injector.select_cashtags([])
        assert result == []


class TestTagInjectorSelectHashtags:

    def test_selects_matching_hashtags(self):
        injector = TagInjector()
        result = injector.select_hashtags(["airdrop", "defi"])
        assert result == ["#Airdrop", "#DeFi"]

    def test_caps_at_five(self):
        injector = TagInjector()
        result = injector.select_hashtags(["airdrop", "testnet", "retroactive", "defi", "nft", "gamefi"])
        assert len(result) == 5

    def test_ignores_unknown_tags(self):
        injector = TagInjector()
        result = injector.select_hashtags(["airdrop", "unknown", "defi"])
        assert result == ["#Airdrop", "#DeFi"]

    def test_case_insensitive_matching(self):
        injector = TagInjector()
        result = injector.select_hashtags(["Airdrop", "DeFi"])
        assert result == ["#Airdrop", "#DeFi"]

    def test_returns_empty_for_no_matches(self):
        injector = TagInjector()
        result = injector.select_hashtags(["xyz"])
        assert result == []


class TestTagInjectorInject:

    def test_appends_tag_line_to_content(self):
        injector = TagInjector()
        result = injector.inject("Hello world", content_tags=["btc", "airdrop"])
        assert result.startswith("Hello world")
        assert "$BTC" in result
        assert "#Airdrop" in result

    def test_strips_existing_tags_before_inject(self):
        injector = TagInjector()
        result = injector.inject("Hello\n\n#DeFi #NFT $BTC", content_tags=["eth", "defi"])
        assert "#NFT" not in result
        assert "$BTC" not in result
        assert "#Airdrop" not in result
        assert "$ETH" in result
        assert "#DeFi" in result

    def test_respects_max_length(self):
        injector = TagInjector()
        long_content = "A" * 4000
        result = injector.inject(long_content, content_tags=["btc", "airdrop"], max_length=100)
        assert len(result) <= 100

    def test_returns_cleaned_content_when_no_tags_match(self):
        injector = TagInjector()
        result = injector.inject("Hello world", content_tags=["unknown"])
        assert result == "Hello world"

    def test_empty_content_with_tags(self):
        injector = TagInjector()
        result = injector.inject("", content_tags=["btc"])
        assert result == "" or "$BTC" in result


class TestStripMarkdown:

    def test_strips_bold(self):
        assert strip_markdown("**bold** text") == "bold text"

    def test_strips_italic(self):
        assert strip_markdown("*italic* text") == "italic text"

    def test_strips_links(self):
        assert strip_markdown("[text](https://example.com)") == "text"

    def test_strips_headings(self):
        assert strip_markdown("## Heading\ncontent") == "Heading\ncontent"

    def test_strips_combined_formatting(self):
        result = strip_markdown("**bold** and *italic* and [link](url)")
        assert result == "bold and italic and link"

    def test_handles_empty_string(self):
        assert strip_markdown("") == ""

    def test_handles_plain_text(self):
        assert strip_markdown("Just plain text") == "Just plain text"


class TestBinanceSquareClient:

    @pytest.mark.asyncio
    async def test_post_content_sends_correct_request(self):
        http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": "000000", "data": {"id": 12345}}
        http_client.post = AsyncMock(return_value=mock_response)

        client = BinanceSquareClient(api_key="test-key", http_client=http_client)
        result = await client.post_content("Hello world")

        assert result == {"code": "000000", "data": {"id": 12345}}
        http_client.post.assert_called_once()
        call_kwargs = http_client.post.call_args.kwargs
        assert call_kwargs["headers"]["X-Square-OpenAPI-Key"] == "test-key"
        assert call_kwargs["headers"]["clienttype"] == "binanceSkill"
        assert call_kwargs["json"] == {"bodyTextOnly": "Hello world"}

    @pytest.mark.asyncio
    async def test_post_content_raises_on_http_error(self):
        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=MagicMock(status_code=401),
        ))

        client = BinanceSquareClient(api_key="test-key", http_client=http_client)
        with pytest.raises(httpx.HTTPStatusError):
            await client.post_content("test")

    @pytest.mark.asyncio
    async def test_post_content_raises_on_timeout(self):
        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        client = BinanceSquareClient(api_key="test-key", http_client=http_client)
        with pytest.raises(httpx.TimeoutException):
            await client.post_content("test")


class TestBinanceSquarePublisher:

    @pytest.mark.asyncio
    async def test_publish_success_returns_url_with_post_id(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        mock_client.post_content.return_value = {"code": "000000", "data": {"id": 67890}}
        publisher = BinanceSquarePublisher(mock_client)
        result = await publisher.publish("Hello **world**")
        assert result.success is True
        assert result.platform == "binance_square"
        assert "67890" in result.url
        mock_client.post_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_daily_limit_220009(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        mock_client.post_content.return_value = {"code": "220009", "message": "Daily limit reached"}
        publisher = BinanceSquarePublisher(mock_client)
        result = await publisher.publish("Hello world")
        assert result.success is False
        assert "220009" in result.error

    @pytest.mark.asyncio
    async def test_publish_empty_content_after_strip(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        publisher = BinanceSquarePublisher(mock_client)
        result = await publisher.publish("")
        assert result.success is False
        assert "Empty content" in result.error

    @pytest.mark.asyncio
    async def test_publish_strips_markdown_before_sending(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        mock_client.post_content.return_value = {"code": "000000", "data": {"id": 1}}
        publisher = BinanceSquarePublisher(mock_client)
        await publisher.publish("**bold** and *italic*")
        sent_text = mock_client.post_content.call_args[0][0]
        assert "**" not in sent_text
        assert "*" not in sent_text

    @pytest.mark.asyncio
    async def test_publish_handles_timeout(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        mock_client.post_content.side_effect = httpx.TimeoutException("timeout")
        publisher = BinanceSquarePublisher(mock_client)
        result = await publisher.publish("Hello world")
        assert result.success is False
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_publish_handles_http_error(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        mock_client.post_content.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock(status_code=500),
        )
        publisher = BinanceSquarePublisher(mock_client)
        result = await publisher.publish("Hello world")
        assert result.success is False
        assert "500" in result.error

    @pytest.mark.asyncio
    async def test_close_does_not_raise(self):
        mock_client = AsyncMock(spec=BinanceSquareClient)
        publisher = BinanceSquarePublisher(mock_client)
        await publisher.close()


class TestTelegramPublisher:

    @pytest.mark.asyncio
    async def test_publish_success_returns_url(self):
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        publisher = TelegramPublisher(bot, chat_id="@test_channel")
        result = await publisher.publish("Hello world")
        assert result.success is True
        assert result.platform == "telegram"
        assert "42" in result.url
        assert result.error is None

        bot.send_message.assert_called_once()
        assert bot.send_message.call_args.kwargs["chat_id"] == "@test_channel"
        assert bot.send_message.call_args.kwargs["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_publish_escapes_html(self):

        bot = AsyncMock()
        bot.send_message = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=1)
        publisher = TelegramPublisher(bot, chat_id="@test")
        await publisher.publish("<script>alert(1)</script> & more")
        sent = bot.send_message.call_args.kwargs["text"]
        assert "&lt;" in sent
        assert "&gt;" in sent
        assert "&amp;" in sent
        assert "<script>" not in sent

    @pytest.mark.asyncio
    async def test_publish_forbidden(self):
        from telegram.error import Forbidden
        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=Forbidden("Bot kicked"))
        publisher = TelegramPublisher(bot, chat_id="@test")
        result = await publisher.publish("Hello")
        assert result.success is False
        assert "kicked" in result.error.lower() or "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_publish_retry_after(self):
        from telegram.error import RetryAfter
        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=RetryAfter(retry_after=30))
        publisher = TelegramPublisher(bot, chat_id="@test")
        result = await publisher.publish("Hello")
        assert result.success is False
        assert "30" in result.error

    @pytest.mark.asyncio
    async def test_publish_bad_request(self):
        from telegram.error import BadRequest
        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=BadRequest("Bad request"))
        publisher = TelegramPublisher(bot, chat_id="@test")
        result = await publisher.publish("Hello")
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_close_does_not_raise(self):
        bot = MagicMock()
        publisher = TelegramPublisher(bot, chat_id="@test")
        await publisher.close()


class TestPublisherConsumerHealth:

    @pytest.mark.asyncio
    async def test_health_check_registration(self):
        publish_queue = AsyncMock()
        system_state = AsyncMock()
        http_client = AsyncMock()
        bot = MagicMock()
        health_collector = MagicMock()

        consumer = PublisherConsumer(
            publish_queue=publish_queue,
            system_state=system_state,
            http_client=http_client,
            binance_api_key="key",
            bot=bot,
            telegram_channel_id="@ch",
            health_collector=health_collector,
        )
        consumer.register_health(health_collector)
        health_collector.register.assert_called_once()
        args = health_collector.register.call_args[0]
        assert args[0] == "publisher"

    @pytest.mark.asyncio
    async def test_health_check_returns_metrics(self):
        publish_queue = AsyncMock()
        system_state = AsyncMock()
        http_client = AsyncMock()
        bot = MagicMock()

        consumer = PublisherConsumer(
            publish_queue=publish_queue,
            system_state=system_state,
            http_client=http_client,
            binance_api_key="key",
            bot=bot,
            telegram_channel_id="@ch",
        )
        consumer._published_ids.add("draft-1")
        consumer._last_publish_time = "2026-01-01T00:00:00Z"
        consumer._last_publish_success = True

        result = await consumer._check_health()
        assert result["last_publish_success"] is True
        assert result["processed_total"] == 1

    @pytest.mark.asyncio
    async def test_shutdown_sets_event(self):
        publish_queue = AsyncMock()
        system_state = AsyncMock()
        http_client = AsyncMock()
        bot = MagicMock()

        consumer = PublisherConsumer(
            publish_queue=publish_queue,
            system_state=system_state,
            http_client=http_client,
            binance_api_key="key",
            bot=bot,
            telegram_channel_id="@ch",
        )
        await consumer.shutdown()
        assert consumer._shutdown.is_set()

    @pytest.mark.asyncio
    async def test_draft_deduplication(self):
        consumer = PublisherConsumer(
            publish_queue=AsyncMock(),
            system_state=AsyncMock(),
            http_client=AsyncMock(),
            binance_api_key="key",
            bot=AsyncMock(),
            telegram_channel_id="@ch",
        )
        consumer._published_ids.add("already-published")
        consumer._shutdown = AsyncMock()
        consumer._shutdown.is_set.return_value = True
        consumer._publish_queue.get = AsyncMock(return_value=MagicMock(title_vn="already-published"))

        with patch.object(consumer, "_publish_to_platforms", AsyncMock()) as mock_pub:
            await consumer._worker()
            mock_pub.assert_not_called()
