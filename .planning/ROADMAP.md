# Project Roadmap — Crypto News & Airdrop Automation Pipeline

## Phase 1: Configuration & Crawler ✅
- Status: Executed (UAT partial)
- Plans: Implementation complete. 16 tests defined in `01-UAT.md`, 1 confirmed.

## Phase 2: AI Handler & Processing 📋
- Status: Planned (4 plans, 17 decisions covered)
- Plans:
  - `02-01-PLAN.md` — DraftContent model + httpx dependency (Wave 1)
  - `02-02-PLAN.md` — Text preprocessor + rate limiter + worker scaffold (Wave 1)
  - `02-03-PLAN.md` — OpenRouter API caller + 2-stage processing + prompt registry (Wave 2)
  - `02-04-PLAN.md` — Wire AI handler into main.py (Wave 2)

## Phase 3: Bot Reviewer & Mode Management ✅
- Status: Shipped — PR #2
- Plans:
  - `03-PLAN.md` — 5 plans in 2 waves
  - Plan 01: Bot Setup & SystemState (Wave 1)
  - Plan 02: Command Handlers (Wave 2)
  - Plan 03: Approval Flow (Wave 2)
  - Plan 04: Edit Flow (Wave 2)
  - Plan 05: AUTO Mode & Guardrails (Wave 2)

## Phase 4: Publisher & Platform Integration ⏳
- Status: Context gathered — ready to plan
- Decisions: 6 areas discussed, 6 decisions captured in `04-CONTEXT.md`

## Phase 5: Resilience, Logging & Monitoring ⏳
- Status: Pending
