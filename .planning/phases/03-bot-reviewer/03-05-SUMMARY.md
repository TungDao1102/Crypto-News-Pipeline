# Plan 03-05 — AUTO Mode & Guardrails — Summary

## Objective
Implement AUTO mode auto-approval, scam detection, low-confidence heuristics, queue backpressure warning, and fallback tracking from AI handler.

## Tasks Completed

### Task 1: Scam detection patterns
- `src/scam_patterns.py` created with 14 SCAM_KEYWORDS: pump, dump, get-rich-quick, guaranteed, double your, risk-free, fast profit, instant profit, no loss, guaranteed return, double your money, get rich, make money fast, 100% profit
- `is_suspicious(text) -> bool` — case-insensitive regex keyword match
- `is_low_confidence(draft, used_fallback) -> bool` — returns True if: used fallback model, body < 100 chars, or fewer than 3 sentences
- **Commit:** `3409f1b`

### Task 2: AUTO mode consumer logic
- In `review_consumer()`: when `mode == "AUTO"`, checks `is_suspicious()` and `is_low_confidence()`
- If both pass: auto-sets `status = "approved"`, pushes to `publish_queue`, increments processed count
- If either fails: forces manual review (sends to admin with inline keyboard)
- Logs: `AUTO approved draft — {title}` / `Forcing manual review (suspicious=X, low_confidence=Y) — {title}`
- **Commit:** `3409f1b`

### Task 3: Queue backpressure
- When pending review count > 50: logs WARNING with queue depth
- In AUTO mode when queue > 50: auto-switches to MANUAL mode + sends alert via HealthCollector
- **Commit:** `3409f1b`

### Task 4: Integration with AI handler
- `src/ai_handler.py` — `call_structured()` now returns `tuple[BaseModel | None, bool]` where bool indicates fallback was used
- `_process_message()` propagates `used_fallback` through translate and rewrite calls
- `src/models.py` — `DraftContent.used_fallback: bool = False` added
- Fallback tracking flows from AI → scam_patterns → review_consumer
- **Commit:** `3409f1b`

## Verification
- 14 scam keywords defined, case-insensitive regex matching
- Low-confidence check: fallback model detection, <100 char body, <3 sentences
- AUTO mode guardrails: suspicious or low-confidence → force manual review
- Queue backpressure threshold at 50 pending
- AUTO mode + overflow >50 → auto-switch to MANUAL mode
- `call_structured()` returns (result, used_fallback) tuple
- `DraftContent.used_fallback` field present in model
- Python syntax valid across all modified files

## Key Decisions
- Scam detection via keyword matching (simple, no ML needed) per AI-SPEC §9
- Low-confidence heuristic: 3-strike rule (fallback model OR <100 chars OR <3 sentences)
- Backpressure auto-switch MANUAL when queue >50 in AUTO mode
- Fallback flag propagated from AI handler through entire pipeline
