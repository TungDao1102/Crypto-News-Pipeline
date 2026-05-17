import asyncio
import hashlib
import logging
import re
import time
from collections import deque

from telethon import TelegramClient, events, errors

from src.config import Config
from src.models import RawMessage

logger = logging.getLogger(__name__)

SCAM_PATTERNS = [
    re.compile(r"(?i)\b(giveaway|free\s+eth|double\s+your|send\s+\d+\s+get\s+\d+|claim\s+your\s+bonus|airdrop\s+scam)\b"),
    re.compile(r"(?i)(t\.me/|https?://)(?!.*\b(?:airdrop|testnet|defi|protocol))"),
    re.compile(r"(?i)\b(seed\s+phrase|private\s+key|login\s+with\s+your)\b"),
]

BACKOFF_INITIAL = 1
BACKOFF_MAX = 300
BACKOFF_MULTIPLIER = 2
BACKOFF_JITTER = 0.1
BACKOFF_MAX_RETRIES = 10

DEDUP_WINDOW = 1000


class TelegramCrawler:
    def __init__(self, config: Config, output_queue: asyncio.Queue) -> None:
        self.client = TelegramClient("telegram.session", config.api_id, config.api_hash)
        self.sources = [s for s in config.sources if s.enabled]
        self.queue = output_queue
        self._seen_texts: deque[str] = deque(maxlen=DEDUP_WINDOW)
        self._shutdown = asyncio.Event()
        self._msg_count_per_source: dict[str, int] = {}
        self._source_paused_until: dict[str, float] = {}

    async def start(self) -> None:
        await self.client.start()
        logger.info("Telegram client connected")

        entities = []
        for i, source in enumerate(self.sources):
            try:
                entity = await self.client.get_entity(source.channel)
                entities.append(entity)
                logger.info("Subscribed to source: %s (tags: %s)", source.channel, source.tags)
            except (ValueError, TypeError, errors.RPCError) as e:
                logger.warning("Skipping invalid source %s: %s", source.channel, e)
                continue
            await asyncio.sleep(1)

        if not entities:
            logger.warning("No valid source channels — crawler has nothing to monitor")
            return

        @self.client.on(events.NewMessage(chats=entities))
        async def handler(event: events.NewMessage.Event) -> None:
            await self._on_message(event)

        self.client.add_event_handler(
            handler,
            events.NewMessage(chats=entities),
        )

        logger.info("Crawler started — listening on %d source(s)", len(entities))
        await self.client.run_until_disconnected()

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        text = event.message.text or (
            event.message.caption if event.message.media else ""
        )
        if not text:
            return

        text = text.strip()

        if len(text) < 50:
            logger.debug("Skipped short message (%d chars) from %s", len(text), event.chat.username)
            return

        if len(text) > 4000:
            logger.warning("Truncated long message (%d chars) from %s", len(text), event.chat.username)
            text = text[:4000]

        channel = event.chat.username or str(event.chat.id)

        for pattern in SCAM_PATTERNS:
            if pattern.search(text):
                logger.warning("Scam pattern detected from %s, skipping", channel)
                return

        self._msg_count_per_source[channel] = self._msg_count_per_source.get(channel, 0) + 1
        if self._msg_count_per_source[channel] > 20:
            self._source_paused_until[channel] = time.time() + 1800
            logger.warning("Source %s paused for 30 min (rate limit)", channel)
            return

        if channel in self._source_paused_until:
            if time.time() < self._source_paused_until[channel]:
                logger.debug("Skipping message from paused source %s", channel)
                return
            del self._source_paused_until[channel]

        text_normalized = re.sub(r"\s+", " ", text).strip().lower()
        content_hash = hashlib.sha256(text_normalized.encode()).hexdigest()

        for seen_text in self._seen_texts:
            similarity = self._text_similarity(text_normalized, seen_text)
            if similarity > 0.8:
                logger.debug("Duplicate message from %s (%.0f%% match)", channel, similarity * 100)
                return

        self._seen_texts.append(text_normalized)

        msg = RawMessage(
            source_channel=channel,
            message_id=event.message.id,
            raw_text=text,
            media_info=event.message.media.__class__.__name__ if event.message.media else None,
            timestamp=event.message.date,
            content_hash=content_hash,
        )
        await self.queue.put(msg)
        logger.debug("Queued message from %s: %.60s...", channel, text)

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    async def shutdown(self) -> None:
        self._shutdown.set()
        await self.client.disconnect()
        logger.info("Crawler disconnected")
