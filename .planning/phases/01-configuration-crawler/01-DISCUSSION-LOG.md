# Phase 1: Configuration & Crawler - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 01-configuration-crawler
**Areas discussed:** Source Channel Management, Crawler Strategy, Message Filtering, Error Handling & Startup

---

## Source Channel Management

| Option | Description | Selected |
|--------|-------------|----------|
| JSON config file (Recommended) | sources.json — easy to add/remove without touching .env. Supports categories, labels per channel. | ✓ |
| .env comma-separated | SOURCE_CHANNELS=@chan1,@chan2 — simple, but changing requires env reload. | |
| Database/DB-driven | Store in SQLite — enables admin to add/remove via bot commands later. | |

**User's choice:** JSON config file (Recommended)
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — categorize channels (Recommended) | Tags like 'airdrop', 'testnet', 'macro'. Helps filtering and routing later. | ✓ |
| No — flat list | All channels treated equally. | |

**User's choice:** Yes — categorize channels (Recommended)
**Notes:** Categories: airdrop, testnet, macro

---

| Option | Description | Selected |
|--------|-------------|----------|
| Load on startup only (Recommended) | Read file at boot, store in memory. Restart to pick up changes. | ✓ |
| Watch file for changes | Use file watcher to detect edits to sources.json and reload dynamically. | |

**User's choice:** Load on startup only (Recommended)
**Notes:** Simpler for v1

---

| Option | Description | Selected |
|--------|-------------|----------|
| No for v1 (Recommended) | Restart to pick up new sources. | ✓ |
| Yes — bot command | Add /add_source and /remove_source commands. | |

**User's choice:** No for v1 (Recommended)
**Notes:** Deferred to Phase 3 (Bot Reviewer)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Array of objects (Recommended) | [{ "channel": "...", "tags": [...], "enabled": true }] | ✓ |
| Map by channel name | { "@channel": { ... } } | |

**User's choice:** Array of objects (Recommended)
**Notes:** Clean, extensible format

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include defaults in repo (Recommended) | sources.default.json with well-known public channels. | ✓ |
| No — user provides their own | Empty sources.json with instructions. | |

**User's choice:** Yes — include defaults in repo (Recommended)
**Notes:** Standard practice for config templates

---

| Option | Description | Selected |
|--------|-------------|----------|
| 3-5 channels (Recommended) | Small set of high-quality international airdrop/testnet channels. | ✓ |
| 5-10 channels | Medium set covering more categories. | |
| 10+ channels | Broad coverage — needs robust dedup from day one. | |

**User's choice:** 3-5 channels (Recommended)
**Notes:** Start small, scale as needed

---

| Option | Description | Selected |
|--------|-------------|----------|
| Keep with enabled: false (Recommended) | Easier to toggle on/off later. | ✓ |
| Remove entirely | Cleaner file, harder to re-enable. | |

**User's choice:** Keep with enabled: false (Recommended)
**Notes:** Prevents losing channel names

---

## Crawler Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Listen for new messages only (Recommended) | Real-time messages only. No duplicate risk. | ✓ |
| Fetch recent history + listen | Last 10-20 messages on startup. Ensures no gap. | |

**User's choice:** Listen for new messages only (Recommended)
**Notes:** Simpler v1; history fetch can be added later

---

| Option | Description | Selected |
|--------|-------------|----------|
| User account + session file (Recommended) | Telethon saves session to .session file. | ✓ |
| Bot token only | Simpler but can't see messages in other channels. | |

**User's choice:** User account + session file (Recommended)
**Notes:** Required for accessing public channel messages

---

| Option | Description | Selected |
|--------|-------------|----------|
| Exponential backoff (Recommended) | AI-SPEC §6.1: initial 1s, max 300s, mult 2, jitter 10% | ✓ |
| Fixed delay between messages | 2-second delay each. Simpler but less responsive. | |

**User's choice:** Exponential backoff (Recommended)
**Notes:** Follows AI-SPEC spec

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential per channel, parallel across channels (Recommended) | One asyncio task per source. | ✓ |
| Single sequential queue | All channels → one queue. Slowest. | |
| Full parallel — all concurrently | Max throughput, no ordering. | |

**User's choice:** Sequential per channel, parallel across channels (Recommended)
**Notes:** Best balance of throughput and ordering

---

## Message Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Text messages only (modified) | Plain text + captions. Filter if message length too short. | ✓ |
| Text + forwarded messages | Also captures forwards from other channels. | |
| All message types | Full capture. May include noisy irrelevant content. | |

**User's choice:** Text messages only, with min length filter
**Notes:** Combined with minimum 50 chars for a two-stage gate

---

| Option | Description | Selected |
|--------|-------------|----------|
| 50+ characters (Recommended) | Filters out short noise. Catches real content. | ✓ |
| No minimum | Process everything. More noise. | |
| 100+ characters | Only substantial posts. May miss short announcements. | |

**User's choice:** 50+ characters (Recommended)
**Notes:** Aligns with "text only + length filter" approach

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — basic filters (Recommended) | Skip known scam keywords, pump/dump language. | ✓ |
| No — send everything to AI | Let AI handler decide quality. Higher risk. | |

**User's choice:** Yes — basic filters (Recommended)
**Notes:** Follows AI-SPEC §9 Guardrails

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — content hash dedup (Recommended) | Normalized text hash, skip if >80% match. | ✓ |
| No | Same news from different sources processed multiple times. | |

**User's choice:** Yes — content hash dedup (Recommended)
**Notes:** Window of recent 1000 messages

---

## Error Handling & Startup

| Option | Description | Selected |
|--------|-------------|----------|
| Clear error message + exit (Recommended) | Print which key is missing/invalid with fix instruction. Exit code 1. | ✓ |
| Create .env from template | Copy .env.example to .env with defaults. | |
| Interactive prompt | Ask user for each missing value via stdin. | |

**User's choice:** Clear error message + exit (Recommended)
**Notes:** Fail fast with actionable message

---

| Option | Description | Selected |
|--------|-------------|----------|
| Log warning + skip channel (Recommended) | Don't crash the whole crawler for one bad source. | ✓ |
| Crash and alert | Exit with error. Forces fix before restart. | |

**User's choice:** Log warning + skip channel (Recommended)
**Notes:** Resilient by default

---

| Option | Description | Selected |
|--------|-------------|----------|
| Log critical error + exit (Recommended) | Session invalid → clear instructions for re-auth. | ✓ |
| Auto-retry with phone/OTP flow | May block in headless/daemon mode. | |

**User's choice:** Log critical error + exit (Recommended)
**Notes:** Headless server won't support interactive OTP

---

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful shutdown on SIGINT/SIGTERM (Recommended) | Disconnect Telethon → flush logs → clean exit. | ✓ |
| Force shutdown | Just kill the process. May leave dangling connections. | |

**User's choice:** Graceful shutdown on SIGINT/SIGTERM (Recommended)
**Notes:** AI-SPEC §4 main.py responsibility

---

## the agent's Discretion

- Exact Telethon client configuration (timeout, retry settings within backoff strategy)
- Log format details beyond the AI-SPEC template
- sources.default.json channel selection (choose 3-5 quality international crypto channels)

## Deferred Ideas

- Runtime add/remove sources via bot command — Phase 3 (Bot Reviewer)
- File watching for dynamic source reload — future enhancement
- Database-backed source list — future enhancement
- History fetch on startup — future enhancement
