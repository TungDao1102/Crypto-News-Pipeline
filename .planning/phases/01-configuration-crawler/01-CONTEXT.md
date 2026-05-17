# Phase 1: Configuration & Crawler - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up project scaffolding, environment configuration, and Telegram message ingestion. Deliverables: `src/config.py` (env validation), `src/crawler.py` (Telethon-based async crawler), `src/models.py` (RawMessage Pydantic model), `src/logging_setup.py` (rotating file + console logging), `sources.json` (source channel config), `src/main.py` (entry point wiring config → crawler → logging). The crawler listens to Telegram channels and produces RawMessage objects for downstream processing (Phase 2).

</domain>

<decisions>
## Implementation Decisions

### Source Channel Management
- **D-01:** JSON config file (`sources.json`) for channel management — not .env or database
- **D-02:** Channels support category tags: `airdrop`, `testnet`, `macro`, etc.
- **D-03:** Source list loaded on startup only — no file watching or runtime reload
- **D-04:** No runtime add/remove in v1 — restart process to pick up changes
- **D-05:** Array-of-objects format: `[{ "channel": "@name", "tags": ["airdrop"], "enabled": true }]`
- **D-06:** Ship `sources.default.json` with well-known public channels as template
- **D-07:** Start with 3-5 source channels
- **D-08:** Disabled channels kept with `enabled: false` (not removed from file)

### Crawler Strategy
- **D-09:** Listen for new messages only — no history fetch on startup
- **D-10:** User account authentication via Telethon `.session` file (not bot token)
- **D-11:** Exponential backoff for rate limiting — initial 1s, max 300s, multiplier 2, ±10% jitter (per AI-SPEC §6.1)
- **D-12:** Sequential processing per channel, parallel across channels (one asyncio task per source)

### Message Filtering
- **D-13:** Text messages only (plain text + captions) — ignore stickers, polls, voice, media-only
- **D-14:** Minimum 50-character length threshold — shorter messages are skipped
- **D-15:** Basic spam/scam keyword filtering — skip known scam patterns per AI-SPEC §9
- **D-16:** Content hash deduplication across sources — normalized text hash comparison, skip if >80% match

### Error Handling & Startup
- **D-17:** `config.py` validates all .env keys on import — clear error message + `exit(1)` on missing/invalid keys
- **D-18:** Invalid source channel (private, banned, non-existent) → log warning + skip channel, don't crash
- **D-19:** Telethon auth failure (expired session) → log critical error + exit with re-auth instructions
- **D-20:** Graceful shutdown on SIGINT/SIGTERM — disconnect Telethon client → flush logs → clean exit

### the agent's Discretion
- Exact Telethon client configuration (timeout, retry settings within backoff strategy)
- Log format details beyond the AI-SPEC template
- sources.default.json channel selection (choose 3-5 quality international crypto channels)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture
- `AI-SPEC.md` §4 — Module structure, file responsibilities, responsibility matrix
- `AI-SPEC.md` §6.1 — Telethon exponential backoff configuration
- `AI-SPEC.md` §6.4 — Logging configuration (RotatingFileHandler, levels per event)
- `AI-SPEC.md` §9 — Guardrails: scam detection, duplicate detection, rate limiting
- `AI-SPEC.md` §10 — Environment configuration spec (.env keys, validation rules)

### Data Models
- `AI-SPEC.md` §4 `models.py` — RawMessage Pydantic model definition

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing codebase

### Established Patterns
- Python async/await with asyncio throughout
- Pydantic v2 for data models and validation
- Telethon v1.x for Telegram client

### Integration Points
- `src/main.py` wires config → crawler, provides RawMessage queue for Phase 2
- `src/models.py` RawMessage is the contract between Phase 1 and Phase 2

</code_context>

<specifics>
## Specific Ideas

- sources.default.json should include 3-5 well-known international crypto airdrop/testnet channels
- Text-message-only with min 50 chars as secondary gate before forwarding to AI pipeline

</specifics>

<deferred>
## Deferred Ideas

- Runtime add/remove sources via bot command — Phase 3 (Bot Reviewer)
- File watching for dynamic source reload — future enhancement
- Database-backed source list — future enhancement

</deferred>

---

*Phase: 01-configuration-crawler*
*Context gathered: 2026-05-17*
