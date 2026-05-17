# Phase 4: Publisher & Platform Integration — Plan Check

**Checker:** Plan Verification Agent
**Date:** 2026-05-17
**Status:** PASS_WITH_RECOMMENDATIONS

---

## Dimension Summary

| Dimension | Result | Notes |
|-----------|--------|-------|
| 1. Requirement Coverage | ✅ PASS | All 6 decisions (D-01 to D-06) have covering tasks |
| 2. Task Completeness | ✅ PASS | All 7 tasks have clear descriptions with files, actions |
| 3. Dependency Correctness | ✅ PASS | Wave 1→2→3 sequencing is logical, no cycles |
| 4. Key Links Planned | ✅ PASS | All critical wiring identified (queue→consumer→platforms) |
| 5. Scope Sanity | ⚠️ WARNING | 7 tasks in single plan exceeds recommended 2-3 |
| 6. Verification Derivation | ✅ PASS | Success criteria are user-observable and testable |
| 7. Context Compliance | ✅ PASS | All 6 decisions addressed, no deferred ideas included |
| 7b. Scope Reduction | ✅ PASS | No silent scope reduction detected |
| 7c. Architectural Tiers | ⏭️ SKIPPED | No Architectural Responsibility Map in RESEARCH.md |
| 8. Nyquist Validation | ⏭️ SKIPPED | No "Validation Architecture" section in RESEARCH.md |
| 9. Cross-Plan Data Contracts | ✅ PASS | No conflicting transforms on shared data entities |
| 10. AGENTS.md Compliance | ⏭️ SKIPPED | No AGENTS.md found |
| 11. Research Resolution | ⏭️ SKIPPED | No Open Questions section in RESEARCH.md |
| 12. Pattern Compliance | ⚠️ WARNING | Plan uses `src/publishers/` but PATTERNS.md recommends `src/publisher/` |

---

## Goal-Backward Verification

### Phase Goal
Consume approved `DraftContent` objects from `publish_queue`, inject platform-required formatting (cashtags, hashtags), publish simultaneously to Telegram Channel (via PTB) and Binance Square (via OpenAPI), track per-platform `PublishResult`, set `DraftContent.status = "published"` when at least one platform succeeds, enforce 2-second cooldown.

### Required Truths Mapping

| # | What Must Be True | Covering Task(s) | Status |
|---|-------------------|-------------------|--------|
| 1 | Consumer reads approved drafts from `publish_queue` | P-06: PublisherConsumer consuming from publish_queue | ✅ |
| 2 | Cashtags/hashtags injected into content before publish | P-02: TagInjector; P-06: consumer calls injector | ✅ |
| 3 | Publish to Telegram via PTB `application.bot.send_message()` | P-04: TelegramPublisher | ✅ |
| 4 | Publish to Binance Square via httpx POST to OpenAPI | P-05: BinanceSquareClient + BinanceSquarePublisher | ✅ |
| 5 | Markdown stripped from content before Binance Square publish | Code Quality section (not in any task action) | ⚠️ |
| 6 | If one platform fails, the other still publishes | Code Quality: D-04 — "log error, continue to next platform" | ✅ |
| 7 | Each publish generates a `PublishResult` with platform, success, url, error | P-03: PublishResult model; P-06: consumer logs results | ✅ |
| 8 | `DraftContent.status` transitions from "approved" → "published" | P-06: "updates DraftContent.status = 'published'" | ✅ |
| 9 | 2-second cooldown between platform publishes | P-06: "2s cooldown"; Code Quality: `asyncio.sleep(2.0)` | ✅ |
| 10 | Publisher consumer wired into main.py event loop | P-07: Wire into bot_reviewer.py / main.py | ✅ |

### Decision Coverage (CONTEXT.md)

| Decision | Description | Covering Task | Status |
|----------|-------------|---------------|--------|
| **D-01** | Reuse PTB `application.bot.send_message()` for Telegram | P-04: TelegramPublisher | ✅ |
| **D-02** | Direct httpx POST to Binance Square OpenAPI | P-05: BinanceSquareClient | ✅ |
| **D-03** | Last-minute injector — strip then inject | P-02: TagInjector; P-06: consumer uses injector | ✅ |
| **D-04** | Continue on partial failure | P-06; Code Quality: D-04 rule | ✅ |
| **D-05** | Per-platform `PublishResult` model | P-03: PublishResult in models.py | ✅ |
| **D-06** | 2-second cooldown between publishes | P-06; Code Quality: `asyncio.sleep(2.0)` | ✅ |

### Deferred Ideas (No Scope Creep)

| Deferred Idea | Included in Plan? | Status |
|---------------|-------------------|--------|
| Media/image for Binance Square | No | ✅ |
| Scheduled/delayed publishing | No | ✅ |
| Publish queue persistence across restarts | No | ✅ |
| Auto-retry with exponential backoff | No (D-04: no retry in v1) | ✅ |
| Multi-worker publisher | No (single consumer) | ✅ |

---

## Issues Found

### Warnings (Should Fix)

#### Warning 1: `src/publishers/` vs `src/publisher/` naming inconsistency

| Field | Detail |
|-------|--------|
| **Dimension** | pattern_compliance |
| **Severity** | warning |
| **Description** | PLAN.md uses `src/publishers/` (with 's') in all task paths and AI-SPEC Conflicts Resolution, but PATTERNS.md recommends `src/publisher/` (without 's'). The plan states "(PATTERNS.md recommendation)" as justification, but PATTERNS.md actually recommends a different path. |
| **Impact** | Executor reading both PLAN.md and PATTERNS.md will see two different directory names. Python imports will break if using the wrong path. |
| **Fix** | Pick one convention and make it consistent across PLAN.md and PATTERNS.md. Recommend `src/publisher/` (shorter, matches module name convention in AI-SPEC §4.2) or `src/publishers/` (if plural package names are preferred). |

#### Warning 2: Markdown stripping for Binance Square is not in any task action

| Field | Detail |
|-------|--------|
| **Dimension** | task_completeness |
| **Severity** | warning |
| **Description** | RESEARCH.md Finding #5 confirms Binance Square does NOT render Markdown. The content pipeline requires `strip_markdown()` before tag injection. This is only mentioned in the "Code Quality" section of PLAN.md ("Binance Square publisher must strip Markdown"), not in any task's `<action>` or description. |
| **Impact** | Executor focused on the task table may build BinanceSquarePublisher without Markdown stripping, resulting in raw Markdown syntax appearing in Binance Square posts. |
| **Fix** | Add a sub-task to P-05 or P-02: "Create `MarkdownStripper` utility or `strip_markdown()` function that converts `**bold**` → `bold`, `*italic*` → `italic`, `[text](url)` → `text (url)`, strips `#` heading markers, removes code fences, and unwraps blockquotes." |

#### Warning 3: 7 tasks in single plan exceeds recommended scope

| Field | Detail |
|-------|--------|
| **Dimension** | scope_sanity |
| **Severity** | warning |
| **Description** | PLAN.md contains 7 tasks and touches ~9 files (7 new + 2 modified). The recommended threshold is 2-3 tasks per plan. |
| **Impact** | Single execution session may exceed context budget. Quality degrades with >5 tasks as context window fills. |
| **Fix** | Consider splitting into 2 plans: Plan A (Wave 1 + Wave 2: base classes, tag injector, model, platform publishers) and Plan B (Wave 3: consumer worker + wiring). Alternatively, keep as-is but note the executor must be efficient. |

#### Warning 4: PublisherConsumer wiring into `run_bot()` is underspecified

| Field | Detail |
|-------|--------|
| **Dimension** | task_completeness |
| **Severity** | warning |
| **Description** | P-07 says "Add `publisher_consumer` creation inside `run_bot()` (has access to `application.bot`)". However, `run_bot()` currently does not receive `http_client` or `binance_api_key`, which are both needed by `PublisherConsumer`. Modifying the function signature is implied but not stated. |
| **Impact** | Executor may not realize `run_bot()` needs new parameters, resulting in a broken wiring on first attempt. |
| **Fix** | Explicitly state in P-07: "Modify `run_bot()` signature to accept `http_client: httpx.AsyncClient` and `binance_api_key: str`. Update the call site in `main.py` to pass these values." |

#### Warning 5: Deduplication mentioned only in Code Quality section

| Field | Detail |
|-------|--------|
| **Dimension** | task_completeness |
| **Severity** | warning |
| **Description** | The Code Quality section mentions "Deduplication via in-memory `set[str]` of published draft IDs to prevent double-publishing." RESEARCH.md §6 also documents this pattern. But no task action explicitly includes deduplication logic. |
| **Impact** | Executor may miss this and risk double-publishing drafts that appear in the queue twice. |
| **Fix** | Add a bullet to P-06's description: "Implement in-memory `_published_ids: set[str]` deduplication set — skip if `draft.id` already published." |

---

## Recommendations

### Before Execution (Fix Warnings)

1. **Resolve `src/publishers/` vs `src/publisher/`** — Choose one path and update both PLAN.md and PATTERNS.md to match. The plan has authority as the execution document, so either update PATTERNS.md to match PLAN.md or vice versa.

2. **Surface Markdown stripping** — Move the `strip_markdown()` requirement from "Code Quality" into the P-05 or P-02 task description. This is critical for Binance Square content quality.

3. **Clarify `run_bot()` wiring** — Add explicit instructions for modifying `run_bot()`'s signature in P-07. The current wording is ambiguous about how `http_client` and `binance_api_key` reach the inner scope.

4. **Surface deduplication** — Add a bullet to P-06's description about the in-memory deduplication set.

### Optional Improvements

5. **Split the plan** — Consider splitting PLAN.md into two execution phases (Foundation + Publishers in one, Integration in another) for better context management. However, the current structure is consistent with Phase 3's approach.

6. **Add `config.py` optional keys** — The optional config keys from PATTERNS.md §5 (`PUBLISH_RETRY_COUNT`, `PUBLISH_COOLDOWN_SECONDS`, etc.) could be hardcoded in v1, but consider noting this decision explicitly.

---

## Conclusion

The plan WILL achieve the Phase 4 goal. All 6 decisions (D-01 to D-06) have covering tasks. The task descriptions are specific and actionable. The wave sequencing is logical. The success criteria are well-defined and testable.

The 5 warnings identified do not block the goal, but addressing them will reduce execution friction and improve code quality. The most impactful fix is surfacing Markdown stripping and deduplication from "Code Quality" notes into explicit task actions, as these are easy to miss during execution.

**Verdict: PASS_WITH_RECOMMENDATIONS** — Proceed with the 5 recommendations above before or during execution.
