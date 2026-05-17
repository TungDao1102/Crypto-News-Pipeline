---
status: testing
phase: 01-configuration-crawler
source: 02-PLAN.md (verification criteria)
started: 2026-05-17T18:55:00Z
updated: 2026-05-17T18:55:00Z
---

## Current Test

number: 1
name: Config validation — missing .env
expected: |
  Running load_config() without .env raises ConfigError with a clear message
  identifying the missing key. No cryptic traceback.
awaiting: user response

## Tests

### 1. Config validation — missing .env
expected: Running load_config() without .env raises ConfigError with a clear message identifying the missing key. No cryptic traceback.
result: [pending]

### 2. Config validation — placeholder detection
expected: .env with "your_" in any value logs a WARNING about default placeholders. System still loads.
result: [pending]

### 3. Config validation — invalid API_HASH
expected: TELEGRAM_API_HASH not exactly 32 characters raises ConfigError with clear message.
result: [pending]

### 4. Config validation — invalid BOT_TOKEN format
expected: TELEGRAM_BOT_TOKEN not matching pattern raises ConfigError with clear message.
result: [pending]

### 5. Sources — auto-copy from default
expected: Running load_config() when sources.json does not exist copies sources.default.json to sources.json automatically.
result: [pending]

### 6. Sources — invalid channel skipped
expected: An invalid/non-existent channel in sources.json logs a WARNING and is skipped. Crawler continues with other channels. No crash.
result: [pending]

### 7. Logging — file and console
expected: setup_logging() creates logs/app.log with RotatingFileHandler. Console output at INFO level, file at DEBUG level.
result: [pending]

### 8. Logging — graceful fallback
expected: If logs/ directory cannot be created, system logs WARNING and continues with console-only logging. No crash.
result: [pending]

### 9. All modules import cleanly
expected: All 5 source modules (models, config, logging_setup, crawler, main) import without errors.
result: [pending]

### 10. Main entry — starts without errors
expected: python src/main.py starts, connects to Telegram (first-time auth may prompt), subscribes to sources, logs readiness.
result: [pending]

### 11. Graceful shutdown
expected: Ctrl+C (SIGINT) or SIGTERM disconnects Telethon client, flushes logs, exits cleanly within 2 seconds. No stuck tasks or traceback on exit.
result: [pending]

### 12. New message appears in log
expected: Sending a message to a monitored channel — a DEBUG log entry appears showing source channel and truncated text. Message queued as RawMessage.
result: [pending]

### 13. Short message skipped
expected: A message shorter than 50 characters is silently skipped. DEBUG log entry shows "Skipped short message".
result: [pending]

### 14. Scam message filtered
expected: A message containing scam keywords (e.g. "giveaway", "private key", suspicious t.me link) is skipped. WARNING log entry shows "Scam pattern detected".
result: [pending]

### 15. Exceed rate limit per source
expected: More than 20 messages from one source in a session — source is paused for 30 min. WARNING log shows "paused for 30 min (rate limit)". Subsequent messages from that source are skipped until timer expires.
result: [pending]

### 16. Duplicate detection across sources
expected: Same message appearing in two source channels — second occurrence is skipped (>80% text match). DEBUG log shows "Duplicate message from X (XX% match)".
result: [pending]

## Summary

total: 16
passed: 0
issues: 0
pending: 16
skipped: 0
blocked: 0

## Gaps

[none yet]
