# Phase 1 Plan: Configuration & Crawler

**Goal:** Project scaffold + environment validation + Telegram message ingestion that produces `RawMessage` objects.

---

## Task Breakdown

### Layer 0: Project Scaffold (no dependencies)
| # | Task | File(s) | Description | Verification |
|---|------|---------|-------------|-------------|
| 0.1 | Create `src/` package | `src/__init__.py` | Empty init, mark as package | `python -c "import src"` succeeds |
| 0.2 | Pin dependencies | `requirements.txt` | `telethon>=1.43,<2`, `pydantic>=2.0,<3`, `python-dotenv>=1.0,<2` | `pip install -r requirements.txt` succeeds |
| 0.3 | Source channel config | `sources.default.json`, `sources.json` | Template with 5 well-known channels + user copy | Valid JSON, follows `[{channel, tags, enabled}]` format |

### Layer 1: Core Infrastructure
| # | Task | File(s) | Depends On |
|---|------|---------|------------|
| 1.1 | Pydantic models | `src/models.py` | 0.1 |
| 1.2 | env validation | `src/config.py` | 0.1, 0.2 |
| 1.3 | Logging setup | `src/logging_setup.py` | 0.1 |

### Layer 2: Crawler
| # | Task | File(s) | Depends On |
|---|------|---------|------------|
| 2.1 | Crawler implementation | `src/crawler.py` | 1.1, 1.2, 1.3 |

### Layer 3: Entry Point
| # | Task | File(s) | Depends On |
|---|------|---------|------------|
| 3.1 | Main wiring | `src/main.py` | 2.1, 1.3 |

---

## Detailed Design

### 0.3 — `sources.default.json`
```json
[
  { "channel": "@AirdropRWA", "tags": ["airdrop"], "enabled": true },
  { "channel": "@testnetmac", "tags": ["testnet"], "enabled": true },
  { "channel": "@DefiLama", "tags": ["defi", "macro"], "enabled": true },
  { "channel": "@CryptoAirdropNews", "tags": ["airdrop"], "enabled": true },
  { "channel": "@airdrops_official", "tags": ["airdrop"], "enabled": false }
]
```
- `sources.json` is user's active file (gitignored)
- `sources.default.json` is template (committed)
- First run copies `default` → active if active missing

### 1.1 — `src/models.py`
- `SourceConfig` — Pydantic `BaseModel` for sources.json entries: `channel: str`, `tags: list[str]`, `enabled: bool = True`
- `RawMessage` — Pydantic `BaseModel` for crawled messages: `source_channel: str`, `message_id: int`, `raw_text: str`, `media_info: str | None`, `timestamp: datetime`, `content_hash: str`
- `ConfigError` — custom `Exception` subclass for fatal configuration issues

### 1.2 — `src/config.py`
- `Config` dataclass holding: `api_id`, `api_hash`, `sources: list[SourceConfig]`
- `load_config()` → validates `.env` exists, parses all keys, returns `Config`
- Validation rules (from AI-SPEC §10):
  - `TELEGRAM_API_HASH` length must be exactly 32 characters
  - `TELEGRAM_API_ID` must be numeric
  - `TELEGRAM_BOT_TOKEN` must match regex `\d+:[\w-]+`
  - **Default-value warning:** log `WARNING` if any value contains `"your_"` (sample placeholders)
- `ConfigError` exception for fatal config issues (missing keys, invalid types)
- Uses `python-dotenv` to load `.env`

### 1.3 — `src/logging_setup.py`
- `setup_logging(level=DEBUG)` → configures root logger per AI-SPEC §6.4
- Creates `logs/` directory if missing (fail gracefully if cannot create, fall back to console-only)
- **Console handler** — level=INFO, format: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- **File handler** — `RotatingFileHandler` at `logs/app.log`, `maxBytes=10MB`, `backupCount=5`, level=DEBUG, same format
- Does NOT return logger; caller uses `logging.getLogger(__name__)`

### 2.1 — `src/crawler.py`
```python
class TelegramCrawler:
    def __init__(self, config: Config, output_queue: asyncio.Queue):
        self.client = TelegramClient(session, config.api_id, config.api_hash)
        self.sources = [s for s in config.sources if s.enabled]
        self.queue = output_queue
        self._seen_hashes: set[str] = set()  # dedup window (LRU, max 1000 entries)
        self._shutdown = asyncio.Event()
        self._msg_count_per_source: dict[str, int] = {}  # rate-limit tracker
        self._source_paused_until: dict[str, float] = {}  # paused sources

    async def start(self):
        await self.client.start()  # interactive auth on first run
        # Stagger get_entity calls with 1s delay to avoid FloodWait
        entities = []
        for i, source in enumerate(self.sources):
            try:
                entity = await self.client.get_entity(source.channel)
                entities.append(entity)
            except (ValueError, TypeError, telethon.errors.RPCError) as e:
                logger.warning(f"⚠️ Skipping invalid source {source.channel}: {e}")
                continue
            await asyncio.sleep(1)  # stagger delay
        if entities:
            @self.client.on(events.NewMessage(chats=entities))
            async def handler(event):
                await self._on_message(event)
        await self.client.run_until_disconnected()

    async def _on_message(self, event):
        # 1. Extract text (plain text + caption, skip media-only)
        text = event.message.text or (event.message.caption if event.message.media else "")
        if not text:
            return
        # 2. Length checks (min 50, max 4000 chars — truncate if over)
        text = text.strip()
        if len(text) < 50:
            logger.debug(f"Skipped short message ({len(text)} chars) from {event.chat.username}")
            return
        if len(text) > 4000:
            logger.warning(f"Truncated long message ({len(text)} chars) from {event.chat.username}")
            text = text[:4000]
        # 3. Scam keyword check
        scam_patterns = [
            r"(?i)\b(giveaway|free\s+eth|double\s+your|send\s+\d+\s+get\s+\d+|claim\s+your\s+bonus|airdrop\s+scam)\b",
            r"(?i)(t\.me/|https?://)(?!.*\bairdrops?|testnet|defi|protocol)",
            r"(?i)\b(seed\s+phrase|private\s+key|login\s+with\s+your)\b",
        ]
        channel = event.chat.username or str(event.chat.id)
        for pattern in scam_patterns:
            if re.search(pattern, text):
                logger.warning(f"⚠️ Scam pattern detected from {channel}, flagging as suspicious")
                # In Phase 1, flag and skip; Phase 3 will handle auto-flag
                return
        # 4. Rate-limit per source — >20 msg/hour → pause 30 min
        self._msg_count_per_source[channel] = self._msg_count_per_source.get(channel, 0) + 1
        if self._msg_count_per_source[channel] > 20:
            self._source_paused_until[channel] = time.time() + 1800  # 30 min
            logger.warning(f"⏸️ Source {channel} paused for 30 min (rate limit)")
            return
        if channel in self._source_paused_until:
            if time.time() < self._source_paused_until[channel]:
                logger.debug(f"Skipping message from paused source {channel}")
                return
            else:
                del self._source_paused_until[channel]  # resume
        # 5. Content hash dedup (>80% match)
        text_normalized = re.sub(r"\s+", " ", text).strip().lower()
        content_hash = hashlib.sha256(text_normalized.encode()).hexdigest()
        # Check similarity against recent hashes
        for seen_hash, seen_text in self._seen_hashes:
            similarity = self._text_similarity(text_normalized, seen_text)
            if similarity > 0.8:
                logger.debug(f"Duplicate message from {channel} ({similarity:.0%} match)")
                return
        self._seen_hashes.add(content_hash)
        # 6. Push RawMessage to queue
        msg = RawMessage(
            source_channel=channel,
            message_id=event.message.id,
            raw_text=text,
            media_info=event.message.media.__class__.__name__ if event.message.media else None,
            timestamp=event.message.date,
            content_hash=content_hash,
        )
        await self.queue.put(msg)
        logger.debug(f"📩 Queued message from {channel}: {text[:60]}...")

    async def shutdown(self):
        self._shutdown.set()
        await self.client.disconnect()
```
- One event handler registered once with all entities (not one per source)
- **Exponential backoff** (AI-SPEC §6.1):
  - Telethon's built-in reconnection handles auto-reconnect
  - Custom reconnect callback implements: `initial_delay=1s`, `max_delay=300s`, `multiplier=2`, `jitter=0.1`, `max_retries=10`
  - After 10 retries → log `CRITICAL` + set `_shutdown` event for graceful stop
- `fetch_history` explicitly deferred to Phase 2 (not implemented in Phase 1)

### 3.1 — `src/main.py`
```python
async def main():
    config = load_config()          # validates .env
    setup_logging()                 # configures logs
    queue: asyncio.Queue[RawMessage] = asyncio.Queue()
    crawler = TelegramCrawler(config, queue)

    # Signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(shutdown(crawler)))

    await crawler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Task Execution Order

```
0.1 (__init__.py) ──────────────────────────────────────────────────────┐
0.2 (requirements.txt) ──► pip install ─────────────────────────────────┤
0.3 (sources.default.json + sources.json) ──────────────────────────────┤
                                                                        ▼
1.1 (models.py) ───────────────────────────────────────────────────► 2.1 (crawler.py)
1.2 (config.py) ───────────────────────────────────────────────────►     │
1.3 (logging_setup.py) ────────────────────────────────────────────►    │
                                                                        ▼
                                                                 3.1 (main.py)
```

---

## Verification Criteria

1. `python -c "from src.config import load_config; cfg = load_config()"` succeeds with valid `.env`, fails with clear message otherwise
2. `python -c "from src.models import RawMessage"` imports cleanly
3. `python -c "from src.logging_setup import setup_logging; setup_logging()"` creates `logs/app.log` with rotating file handler
4. `python src/main.py` starts, connects to Telegram (needs first-time auth), subscribes to sources
5. On Ctrl+C, process exits cleanly within 2 seconds (no stuck tasks)
6. Sending a message to a monitored channel appears in crawler log as DEBUG
7. Sources with `enabled: false` are silently skipped (no connection attempt)
8. Invalid channel in sources → log warning, skip, don't crash
9. `.env` with `your_` default values → log WARNING about placeholder values
10. Message <50 chars → silently skipped (log DEBUG)
11. Message >4000 chars → truncated to 4000 (log WARNING)
12. Message matching scam pattern → skipped (log WARNING)
13. >20 messages from one source in a session → source paused (log WARNING)

---

## Files to Create (7 new files)

| File | Size est. | Purpose |
|------|-----------|---------|
| `src/__init__.py` | 0 lines | Package marker |
| `requirements.txt` | 3 lines | Dependencies |
| `sources.default.json` | 15 lines | Channel template |
| `src/models.py` | ~50 lines | Pydantic/ dataclass models |
| `src/config.py` | ~80 lines | Env validation + config loading |
| `src/logging_setup.py` | ~40 lines | Logging configuration |
| `src/crawler.py` | ~120 lines | Telegram crawler with filtering |
| `src/main.py` | ~50 lines | Entry point |

**Total: ~360 lines of Python**

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| First-time Telethon auth blocks pipeline | High | Log clear instructions; `start()` handles interactive mode |
| Telethon session expires after inactivity | Medium | Detect via auth error → log critical + exit with re-auth instructions |
| FloodWait on startup connecting to many channels | Medium | Stagger `get_entity` calls with 1s delay |
| Content hash dedup misses near-identical messages | Low | Accept false negatives; Phase 2 can add AI-level dedup |
| `asyncio.Queue` unbounded growth | Low | Phase 1 produces slowly; Phase 2 will add backpressure |
