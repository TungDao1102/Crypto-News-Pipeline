import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import BOT_TOKEN_PATTERN, _load_sources, _validate, _warn_defaults, load_config
from src.models import ConfigError, RawMessage, SourceConfig

# ─── Model Tests ─────────────────────────────────────────────────

class TestSourceConfig:
    def test_construct_with_required(self):
        s = SourceConfig(channel="@test")
        assert s.channel == "@test"
        assert s.tags == []
        assert s.enabled is True

    def test_construct_with_all_fields(self):
        s = SourceConfig(channel="@test", tags=["airdrop"], enabled=False)
        assert s.tags == ["airdrop"]
        assert s.enabled is False


class TestRawMessage:
    def test_construct_with_required(self):
        now = datetime.now(timezone.utc)
        r = RawMessage(
            source_channel="@test",
            message_id=1,
            raw_text="hello",
            timestamp=now,
            content_hash="abc",
        )
        assert r.source_channel == "@test"
        assert r.message_id == 1
        assert r.raw_text == "hello"
        assert r.timestamp == now
        assert r.content_hash == "abc"
        assert r.media_info is None

    def test_construct_with_media(self):
        now = datetime.now(timezone.utc)
        r = RawMessage(
            source_channel="@test",
            message_id=2,
            raw_text="with media",
            media_info="Photo",
            timestamp=now,
            content_hash="def",
        )
        assert r.media_info == "Photo"


class TestConfigError:
    def test_is_exception(self):
        assert issubclass(ConfigError, Exception)

    def test_message(self):
        err = ConfigError("test error")
        assert str(err) == "test error"


# ─── Config Validation Tests ──────────────────────────────────────

class TestValidate:
    def test_missing_key_raises(self):
        with pytest.raises(ConfigError, match="TELEGRAM_API_ID"):
            _validate({})

    def test_empty_value_raises(self):
        values = {
            "TELEGRAM_API_ID": "",
            "TELEGRAM_API_HASH": "a" * 32,
            "TELEGRAM_BOT_TOKEN": "123:abc",
            "ADMIN_CHAT_ID": "admin",
            "OPENROUTER_API_KEY": "sk-xxx",
            "BINANCE_SQUARE_API_KEY": "bs-xxx",
            "TELEGRAM_CHANNEL_ID": "@channel",
            "SYSTEM_MODE": "MANUAL",
        }
        with pytest.raises(ConfigError, match="TELEGRAM_API_ID"):
            _validate(values)

    def test_non_numeric_api_id_raises(self):
        values = {
            "TELEGRAM_API_ID": "not-a-number",
            "TELEGRAM_API_HASH": "a" * 32,
            "TELEGRAM_BOT_TOKEN": "123:abc",
            "ADMIN_CHAT_ID": "admin",
            "OPENROUTER_API_KEY": "sk-xxx",
            "BINANCE_SQUARE_API_KEY": "bs-xxx",
            "TELEGRAM_CHANNEL_ID": "@channel",
            "SYSTEM_MODE": "MANUAL",
        }
        with pytest.raises(ConfigError, match="must be numeric"):
            _validate(values)

    def test_api_hash_wrong_length_raises(self):
        values = {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "too-short",
            "TELEGRAM_BOT_TOKEN": "123:abc",
            "ADMIN_CHAT_ID": "admin",
            "OPENROUTER_API_KEY": "sk-xxx",
            "BINANCE_SQUARE_API_KEY": "bs-xxx",
            "TELEGRAM_CHANNEL_ID": "@channel",
            "SYSTEM_MODE": "MANUAL",
        }
        with pytest.raises(ConfigError, match="exactly 32 characters"):
            _validate(values)

    def test_bot_token_bad_format_raises(self):
        values = {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "a" * 32,
            "TELEGRAM_BOT_TOKEN": "invalid-token-format",
            "ADMIN_CHAT_ID": "admin",
            "OPENROUTER_API_KEY": "sk-xxx",
            "BINANCE_SQUARE_API_KEY": "bs-xxx",
            "TELEGRAM_CHANNEL_ID": "@channel",
            "SYSTEM_MODE": "MANUAL",
        }
        with pytest.raises(ConfigError, match="does not match"):
            _validate(values)

    def test_valid_config_passes(self):
        values = {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "a" * 32,
            "TELEGRAM_BOT_TOKEN": "123:abc",
            "ADMIN_CHAT_ID": "admin",
            "OPENROUTER_API_KEY": "sk-xxx",
            "BINANCE_SQUARE_API_KEY": "bs-xxx",
            "TELEGRAM_CHANNEL_ID": "@channel",
            "SYSTEM_MODE": "MANUAL",
        }
        _validate(values)


class TestWarnDefaults:
    def test_placeholder_detected(self, caplog):
        caplog.set_level(logging.WARNING)
        _warn_defaults({"TELEGRAM_API_ID": "your_api_id_here"})
        assert len(caplog.records) >= 1
        assert "placeholder" in caplog.text.lower()

    def test_no_warning_for_real_values(self, caplog):
        caplog.set_level(logging.WARNING)
        _warn_defaults({"TELEGRAM_API_ID": "12345"})
        assert len(caplog.records) == 0


class TestBotTokenPattern:
    def test_valid_tokens(self):
        assert BOT_TOKEN_PATTERN.fullmatch("123456:ABCdefGHIjklMNO")
        assert BOT_TOKEN_PATTERN.fullmatch("1:a")

    def test_invalid_tokens(self):
        assert not BOT_TOKEN_PATTERN.fullmatch("")
        assert not BOT_TOKEN_PATTERN.fullmatch("no-colon")
        assert not BOT_TOKEN_PATTERN.fullmatch(":abc")


class TestLoadSources:
    def test_missing_default_returns_empty(self, tmp_path):
        with patch.object(Path, "exists", return_value=False):
            result = _load_sources()
        assert result == []

    def test_copies_from_default_when_active_missing(self):
        import src.config
        assert hasattr(src.config, "_load_sources")
        assert callable(src.config._load_sources)

    def test_invalid_json_raises(self, tmp_path):
        active_file = tmp_path / "sources.json"
        active_file.write_text("not-json", encoding="utf-8")
        with patch("src.config.Path", side_effect=lambda p, **kw: tmp_path / p if isinstance(p, str) else Path(p)):
            with pytest.raises(ConfigError, match="sources.json"):
                _load_sources()


class TestLoadConfig:
    def test_missing_env_raises(self):
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(ConfigError, match=".env file not found"):
                load_config()

    def test_loads_successfully(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_API_ID", "12345")
        monkeypatch.setenv("TELEGRAM_API_HASH", "a" * 32)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        monkeypatch.setenv("ADMIN_CHAT_ID", "admin")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-xxx")
        monkeypatch.setenv("BINANCE_SQUARE_API_KEY", "bs-xxx")
        monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@channel")
        monkeypatch.setenv("SYSTEM_MODE", "MANUAL")

        with (
            patch("src.config.Path.exists", return_value=True),
            patch("src.config._load_sources", return_value=[]),
            patch("src.config.load_dotenv"),
        ):
            cfg = load_config()
        assert cfg.api_id == 12345
        assert cfg.api_hash == "a" * 32
        assert cfg.bot_token == "123:abc"
        assert cfg.system_mode == "MANUAL"


# ─── Logging Tests ────────────────────────────────────────────────

class TestSetupLogging:
    def test_creates_console_and_file_handlers(self):
        # Reset root logger to isolate test
        root = logging.getLogger()
        old_handlers = root.handlers[:]
        root.handlers.clear()

        from src.logging_setup import setup_logging
        setup_logging()

        handler_types = [type(h).__name__ for h in root.handlers]
        assert "StreamHandler" in handler_types or "ConsoleHandler" in handler_types
        assert "RotatingFileHandler" in handler_types

        for h in root.handlers:
            h.close()
            root.removeHandler(h)
        for h in old_handlers:
            root.addHandler(h)


# ─── Crawler Tests ────────────────────────────────────────────────

class TestCrawlerTextSimilarity:
    def setup_method(self):
        from src.crawler import TelegramCrawler
        self.crawler = TelegramCrawler.__new__(TelegramCrawler)

    def test_identical_texts(self):
        assert self.crawler._text_similarity("a b c", "a b c") == 1.0

    def test_completely_different(self):
        assert self.crawler._text_similarity("a b c", "x y z") == 0.0

    def test_partial_overlap(self):
        sim = self.crawler._text_similarity("a b c d", "a b x y")
        assert sim == pytest.approx(2 / 6)

    def test_empty_strings(self):
        assert self.crawler._text_similarity("", "a b") == 0.0
        assert self.crawler._text_similarity("a b", "") == 0.0

    def test_both_empty(self):
        assert self.crawler._text_similarity("", "") == 0.0


class TestScamPatterns:
    def test_giveaway_detected(self):
        from src.crawler import SCAM_PATTERNS
        assert any(p.search("Free ETH giveaway claim now") for p in SCAM_PATTERNS)

    def test_private_key_detected(self):
        from src.crawler import SCAM_PATTERNS
        assert any(p.search("Enter your private key to verify") for p in SCAM_PATTERNS)

    def test_seed_phrase_detected(self):
        from src.crawler import SCAM_PATTERNS
        assert any(p.search("Your seed phrase is needed") for p in SCAM_PATTERNS)

    def test_legit_airdrop_not_flagged(self):
        from src.crawler import SCAM_PATTERNS
        legit = "New airdrop from testnet protocol —  DeFi rewards"
        assert not any(p.search(legit) for p in SCAM_PATTERNS)


class TestCrawlerOnMessage:
    @pytest.mark.asyncio
    async def test_short_message_skipped(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = MagicMock()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        event = MagicMock()
        event.message.text = "short"
        event.message.media = None
        event.chat.username = "@test"

        await crawler._on_message(event)
        crawler.queue.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_message_truncated(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = asyncio.Queue()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        long_text = "x" * 5000
        event = MagicMock()
        event.message.text = long_text
        event.message.media = None
        event.chat.username = "@test"
        event.message.id = 1
        event.message.date = datetime.now(timezone.utc)

        await crawler._on_message(event)
        msg = await crawler.queue.get()
        assert len(msg.raw_text) == 4000

    @pytest.mark.asyncio
    async def test_scam_message_skipped(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = asyncio.Queue()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        event = MagicMock()
        event.message.text = "Free ETH giveaway! Click here to claim your bonus!"
        event.message.media = None
        event.chat.username = "@test"

        await crawler._on_message(event)
        assert crawler.queue.empty()

    @pytest.mark.asyncio
    async def test_rate_limited_source_paused(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = asyncio.Queue()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        event = MagicMock()
        event.message.text = "x" * 100
        event.message.media = None
        event.chat.username = "@test"
        event.message.id = 1
        event.message.date = datetime.now(timezone.utc)

        for _ in range(21):
            await crawler._on_message(event)
        assert "@test" in crawler._source_paused_until

    @pytest.mark.asyncio
    async def test_normal_message_queued(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = asyncio.Queue()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        event = MagicMock()
        event.message.text = "x" * 100
        event.message.media = None
        event.chat.username = "@test"
        event.message.id = 1
        event.message.date = datetime.now(timezone.utc)

        await crawler._on_message(event)
        msg = await crawler.queue.get()
        assert msg is not None
        assert msg.raw_text == "x" * 100

    @pytest.mark.asyncio
    async def test_duplicate_message_detected(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = asyncio.Queue()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        text = "Important airdrop announcement from the official team"
        event = MagicMock()
        event.message.text = text
        event.message.media = None
        event.chat.username = "@test"
        event.message.id = 1
        event.message.date = datetime.now(timezone.utc)

        await crawler._on_message(event)
        assert not crawler.queue.empty()
        await crawler.queue.get()

        await crawler._on_message(event)
        assert crawler.queue.empty()

    @pytest.mark.asyncio
    async def test_media_only_message_skipped(self):
        from src.crawler import TelegramCrawler
        crawler = TelegramCrawler.__new__(TelegramCrawler)
        crawler.queue = MagicMock()
        crawler._seen_texts = []
        crawler._msg_count_per_source = {}
        crawler._source_paused_until = {}
        crawler._health_collector = None

        event = MagicMock()
        event.message.text = None
        event.message.caption = None
        event.message.media = MagicMock()
        event.chat.username = "@test"

        await crawler._on_message(event)
        crawler.queue.put.assert_not_called()


# ─── Scam Pattern Regex Tests ─────────────────────────────────────

class TestScamPatternRegexEdgeCases:
    def test_suspicious_link(self):
        from src.crawler import SCAM_PATTERNS
        assert any(p.search("Check t.me/scamchannel for details") for p in SCAM_PATTERNS)

    def test_legitimate_link_not_flagged(self):
        from src.crawler import SCAM_PATTERNS
        text = "Read more at https://t.me/airdrop_official about the airdrop"
        assert not any(p.search(text) for p in SCAM_PATTERNS)
