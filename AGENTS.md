# AGENTS.md — CrowdWise Autonomy & Integrity Contract

## 0. Autonomy Contract
- Act as an autonomous senior team (full-stack, backend, data, ML, DBA, UI/UX).
- Owner is unavailable (exams). Plan, build, test, debug, and integrate autonomously.
- Read `docs/MASTER_SPEC.md` to prevent drift. Official briefs supersede prompt assumptions.
- Time-box rule: 3 different failed attempts -> simplest working alternative + log it.
- Never fake API responses, ML outputs, or integrations. "Done" means executed and tested.
- No secrets in code/logs/git. Use `.env` (commit `.env.example` only).

## 2. Four-Tier Data Provenance Rules (Non-Negotiable)
Every API payload and UI component displaying data must declare its provenance tier:
1. `real_public`: Delhi Buses static GTFS (routes, stops, timetable) from Delhi Transport Stack.
2. `organizer`: Real ETM / e-ticketing data supplied by hackathon organizers.
3. `demo_synthetic`: Tickets produced by our built-in simulator (`scripts/generate_demo_data.py`).
4. `estimated`: Any inferred or modelled values (must name the method).

### Crucial Invariants
- `DATA_MODE=demo` until organizer data is loaded: persistent top banner + "Simulated" chips everywhere.
- GTFS times are scheduled/timetable times — never claim live or actual.
- Ticket counts != passengers on board. Output is Relative Crowding Index (0–100, Low/Mod/High) + Confidence.
- Occupancy % is shown ONLY if verified capacity AND documented expansion factor exist; else hide + tooltip.
- Alightings inferred under Mode B must be explicitly flagged as `estimated`.
- Hash or drop all personal identifiers (card/phone numbers) at ingestion (DPDP Act compliance).

## 4. Technology Stack
- **Frontend**: React 18, Vite, JavaScript, Tailwind CSS, React Router, Axios, Recharts, Leaflet / react-leaflet.
- **Backend**: Python 3.11+, Flask, Flask-CORS, SQLAlchemy 2.x ORM, Pydantic v2, python-dotenv, gunicorn.
- **ML / Data**: pandas, numpy, scikit-learn (RandomForestRegressor), joblib, pyarrow (parquet), PyYAML.
- **Database**: SQLite default (zero-setup), PostgreSQL via `DATABASE_URL` / `docker-compose.yml`.
- **Testing**: pytest, `scripts/smoke_test.py`, `scripts/doctor.py`.

## 18. Definition of Done Checklist
- [ ] Fresh clone + `python scripts/bootstrap.py --demo` yields fully functioning system.
- [ ] 5 core frontend pages operational on real API data, 0 console errors, mobile (390px) responsive.
- [ ] Provenance chips visible on every crowd metric; demo banner active in demo mode.
- [ ] Direct route journey planner with 3 presets (Fastest, Balanced, Least crowded) + transparent scores.
- [ ] Chronological ML split verified (`max(train) < min(val) < min(test)`) with no leakage.
- [ ] Peak vs off-peak sanity checks PASS or report honest WARN.
- [ ] Empty database and missing model handle gracefully without 500 errors.
- [ ] `scripts/swap_data.py` verified end-to-end for one-command switch to organizer data.
- [ ] Hackathon pack (`PROPOSAL.md`, `TECHNICAL_NOTE.md`, `DEMO_SCRIPT.md`, `MANUAL_TODO.md`) complete.

