---
status: validated
phase: 01-configuration-crawler
source: 02-PLAN.md (verification criteria)
updated: 2026-05-24T12:01:00Z
---

## Automated Tests

All 16 UAT cases are covered by automated tests in `tests/test_phase1.py` (40 tests).
Run: `python -m pytest tests/test_phase1.py -v`

## Tests

### 1. Config validation — missing .env
expected: Running load_config() without .env raises ConfigError with a clear message identifying the missing key. No cryptic traceback.
result: pass
coverage: test_missing_env_raises

### 2. Config validation — placeholder detection
expected: .env with "your_" in any value logs a WARNING about default placeholders. System still loads.
result: pass
coverage: test_placeholder_detected

### 3. Config validation — invalid API_HASH
expected: TELEGRAM_API_HASH not exactly 32 characters raises ConfigError with clear message.
result: pass
coverage: test_api_hash_wrong_length_raises

### 4. Config validation — invalid BOT_TOKEN
expected: BOT_TOKEN not matching expected format raises ConfigError.
result: pass
coverage: test_bot_token_bad_format_raises

### 5. Config validation — invalid API_ID
expected: TELEGRAM_API_ID not a valid integer raises ConfigError.
result: pass
coverage: test_non_numeric_api_id_raises

### 6. Config validation — valid config loads
expected: All required fields present and valid returns Config instance.
result: pass
coverage: test_valid_config_passes + test_loads_successfully

### 7. Sources — valid JSON loaded
expected: sources.json with valid JSON array returns list of SourceConfig.
result: pass
coverage: test_loads_successfully (within)

### 8. Sources — invalid JSON raises error
expected: sources.json with invalid JSON syntax raises ConfigError with helpful message.
result: pass
coverage: test_invalid_json_raises

### 9. Sources — default copied when active missing
expected: sources.json missing, sources.default.json exists → copied to sources.json.
result: pass
coverage: test_copies_from_default_when_active_missing

### 10. Sources — placeholder URLs warned
expected: sources.json contains "https://t.me/your_channel" → warning logged.
result: pass
coverage: test_placeholder_detected (warns for any placeholder pattern)

### 11. Crawler — short message skipped
expected: Message shorter than configured MIN_MESSAGE_LENGTH is not forwarded. Crawler silently drops it.
result: pass
coverage: test_short_message_skipped

### 12. Crawler — long message truncated
expected: Message exceeding configured MAX_MESSAGE_LENGTH truncated to max length in RawMessage.
result: pass
coverage: test_long_message_truncated

### 13. Crawler — scam detected
expected: Message matching scam patterns (giveaway, seed phrase, private key) is logged as WARNING and not forwarded.
result: pass
coverage: test_scam_message_skipped + TestScamPatterns (5 tests)

### 14. Crawler — dedup
expected: Duplicate text in recent window (defined by config) is not forwarded.
result: pass
coverage: test_duplicate_message_detected + TestCrawlerTextSimilarity (5 tests)

### 15. Crawler — rate limit
expected: Same source sends more than 1 message within rate-limit window → source paused, WARNING logged.
result: pass
coverage: test_rate_limited_source_paused

### 16. Crawler — media-only skipped
expected: Message with media but no text is not forwarded.
result: pass
coverage: test_media_only_message_skipped

## Summary

total: 16
passed: 16
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
