# Phase 1: Configuration & Crawler — Research

## RESEARCH COMPLETE

### Key Technologies

| Technology | Version | Notes |
|-----------|---------|-------|
| Telethon | 1.43.2 (latest, Apr 2026) | Full async MTProto client. Session-file auth. Built-in FloodWaitError handling. |
| Pydantic | v2 | Schema validation, BaseModel for data contracts |
| Python | 3.10+ | asyncio built-in, async/await syntax |
| OpenRouter API | OpenAI-compatible | `response_format` with `json_schema` for structured outputs |

### Telethon Architecture Patterns

1. **Event-driven listening** — Use `@client.on(events.NewMessage)` for real-time capture. Each channel gets its own event stream but event handlers run in the same event loop.

2. **Session persistence** — Telethon saves session to `.session` file after first auth. Subsequent runs reuse it. Store in `.gitignore`d location.

3. **Rate limit handling** — `errors.FloodWaitError` has a `.seconds` attribute. Use exponential backoff: initial 1s → max 300s → multiplier 2 → ±10% jitter.

4. **Connection lifecycle** — `client.start()` → `client.run_until_disconnected()` → graceful shutdown via `client.disconnect()`. Signal handlers (SIGINT/SIGTERM) should call disconnect.

5. **Multi-channel architecture** — One `TelegramClient` can subscribe to multiple channels. Use `client.get_entity(channel_username)` to resolve channel handles, then track via `events.NewMessage(chats=[entity])`.

### OpenRouter Structured Outputs

1. **Endpoint:** `POST https://openrouter.ai/api/v1/chat/completions`
2. **Auth:** `Authorization: Bearer <OPENROUTER_API_KEY>` header
3. **Structured outputs:** Set `response_format: { "type": "json_schema", "json_schema": { ... } }`
4. **Free models:** `deepseek-chat:free`, `meta-llama/llama-3-70b-instruct:free`, `qwen/qwen-2.5-72b-instruct:free`
5. **Fallback strategy:** Try models in order; on 429/5xx, wait 2s then try next in chain

### AsyncIO Best Practices

1. **Producer-Consumer pattern:** Use `asyncio.Queue` to decouple crawler (producer) from AI handler (consumer)
2. **Graceful shutdown:** Use `asyncio.Event` as shutdown signal. Set on SIGINT/SIGTERM, check in main loop.
3. **Task management:** Use `asyncio.gather()` to run parallel tasks. Track with `asyncio.TaskGroup` (Python 3.11+).
4. **Logging:** `logging` with `RotatingFileHandler` (10MB, 5 backups). Async logger via `QueueHandler/QueueListener`.

### Project Structure Considerations

- Use `python-dotenv` for `.env` loading
- `requirements.txt` should pin: `telethon>=1.43,<2`, `pydantic>=2.0,<3`, `python-dotenv>=1.0,<2`, `httpx>=0.27,<1`
- Session file should be in project root (gitignored) or configurable path
- `sources.json` format: array of objects with `channel`, `tags[]`, `enabled` fields

### Potential Pitfalls

- **First-time auth:** Telethon needs phone number + OTP on first run. Must handle interactively or document clearly.
- **FloodWait on startup:** Multiple rapid connection attempts trigger flood wait. Use backoff from the start.
- **Session expiration:** Sessions can expire after weeks of inactivity. Must detect and alert Admin.
- **Memory leaks:** Long-running Telethon clients may accumulate event handlers. Ensure cleanup on shutdown.
- **Message dedup:** Same airdrop news often appears in multiple channels. Content hash dedup is essential to prevent duplicates in queue.
