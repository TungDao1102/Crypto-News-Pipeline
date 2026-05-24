# Phase 1: Configuration & Crawler — Summary

## Objective
Project scaffold, environment validation, config loading, logging setup, and Telegram message ingestion producing `RawMessage` objects.

## Tasks Completed

### Layer 0: Project Scaffold
- `src/__init__.py` — package marker
- `requirements.txt` — telethon>=1.43, pydantic>=2.0, python-dotenv>=1.0
- `sources.default.json` — template with 5 well-known channels
- **Commit:** `89bd8c6`

### Layer 1: Core Infrastructure
- `src/models.py` — SourceConfig, RawMessage, ConfigError (Pydantic v2)
- `src/config.py` — Config class, `load_config()` with env validation, source loading, placeholder detection
- `src/logging_setup.py` — `setup_logging()` with RotatingFileHandler, console handler
- **Commit:** `89bd8c6`

### Layer 2: Crawler
- `src/crawler.py` — TelegramCrawler with: Telethon event handler, content dedup (Jaccard similarity >80%), rate limiting per source (>20 msg/h → 30min pause), scam pattern filtering, exponential backoff reconnect (max 10 retries)
- **Commit:** `89bd8c6`

### Layer 3: Main Entry Point
- `src/main.py` — async main() with crawler startup, signal handlers (SIGINT/SIGTERM), graceful shutdown
- **Commit:** `89bd8c6`

## Verification
- All 5 source modules import cleanly
- Config validation: missing .env raises ConfigError, placeholders log WARNING
- Sources auto-copy from sources.default.json when sources.json missing
- Logging creates rotating file handler + console handler

## Key Decisions
- Telethon for Telegram MTProto (not a bot-only library)
- Pydantic v2 BaseModel for all data models
- Single event handler registered with all entities (not one per source)
- Content dedup via Jaccard similarity on token sets (>80% match)
- Rate limiting per source: 20 msg/h threshold → 30 min pause
- Exponential backoff: 1s initial, 300s max, 2x multiplier, 0.1 jitter, 10 max retries
- Scam filtering via regex patterns in Phase 1 (flag + skip; Phase 3 enhances)
- `fetch_history` explicitly deferred to later phases
