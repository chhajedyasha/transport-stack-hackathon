# MANUAL_TODO.md — Owner Action Checklist

This document details the exact items that require manual owner intervention, why they are needed, and the autonomous fallback currently in place.

---

## Summary: What the System Handles vs. What the Owner Needs to Do

| Category | What the Autonomous Team Does | What YOU (Owner) Need to Do |
|---|---|---|
| **Code & Architecture** | 100% complete (Frontend, Backend, ML, Scripts) | None |
| **GTFS Static Data** | Ingests real Delhi Buses GTFS (or fictional fixture if blocked) | None (auto-downloaded/mocked) |
| **Ticketing Data** | Generates high-fidelity synthetic demo tickets with ground truth | Drop official organizer files when received |
| **Model Training** | Trains baseline & Random Forest models with leakage checks | None |
| **Testing & Sanity** | 100% automated pytest & smoke tests | None |
| **Documentation** | Drafts proposal, technical note, and demo script | Review & submit for hackathon |
| **Deployment** | Configures Docker, Gunicorn, Vercel & Render configs | Add production tokens/accounts if hosting |

---

## Action Items for Owner (When Available)

### 1. Hackathon Official Organizer Dataset (ETM Data)
- **Status:** **PROCESSED, TRAINED & ACTIVE IN PRODUCTION** (`backend/crowdwise.db`).
- **File Details:** 290 MB, 2,559,899 actual Delhi ETM transaction records (October 1–31, 2026).
- **Execution:** Processed end-to-end via `scripts/process_october_tickets.py` with 519,584 demand facts loaded and ML models retrained (`data_mode = 'organizer'`).
- **Provenance:** Fully active under `active_tier: organizer` (`is_demo: false`). Zero further manual ingestion required.

### 2. Vehicle Capacity & Expansion Factor Confirmation
- **Status:** In config flagged as `assumption: true`.
- **Why:** Real ETM data represents only a fraction of total bus riders (free women passes, monthly passes, cash tickets).
- **Your Action:** Check if organizers specify:
  - Bus capacity (default assumption: 60 passengers for standard DTC buses).
  - Expansion factor (default assumption: 2.5x to account for non-ticketed/pass travel).
  - If official numbers exist, update `config/capacity_by_bus_type.yaml` and set `capacity_verified: true`.

### 3. Video Pitch Recording (Phase 1 Submission)
- **Status:** Video script and slide deck outline generated in `docs/DEMO_SCRIPT.md`.
- **Your Action:**
  1. Read through `docs/DEMO_SCRIPT.md` (3-minute timed script).
  2. Open the running CrowdWise app (`http://localhost:5000`).
  3. Record a 3-minute screen capture following the exact click walkthrough.

### 4. Proposal Document Submission
- **Status:** Draft prepared in `docs/PROPOSAL.md`.
- **Your Action:** Review the two-page proposal, insert team member names/emails, and upload it to the hackathon submission portal before the Phase 1 deadline.

### 5. Optional Production Cloud Deployment
- **Status:** Local zero-setup SQLite and Docker Compose Postgres ready.
- **Your Action (if you want a live public URL for judges):**
  - Backend: Connect GitHub repo to Render / Railway.
  - Frontend: Connect GitHub repo to Vercel / Netlify.
  - Database: Connect free Supabase / Neon PostgreSQL via `DATABASE_URL`.

