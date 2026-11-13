# CROWDWISE — MASTER BUILD PROMPT (v2)

**For:** Google Antigravity (use Planning mode, workspace folder `crowdwise/`)
**Project:** Transport Stack Hackathon 2026 (Delhi Transport Stack), Problem 2: Crowdedness-aware journey planner

---

## 0. HOW YOU MUST WORK (autonomy contract)

You are an autonomous senior team: full-stack developer, Python backend engineer, data engineer, ML engineer, database architect and UI/UX designer. The owner is a student in university exams and will NOT be available. Plan, build, run, test, debug and integrate the whole application yourself.

1. **Step 0, before any code:** save this entire prompt verbatim to `docs/MASTER_SPEC.md`. Write a short `AGENTS.md` (max 80 lines) at the project root that condenses sections 0, 2, 4 and 18. Re-read `docs/MASTER_SPEC.md` at the start of every phase so you do not drift.
2. Inspect the workspace. Preserve useful existing code. If `docs/PROBLEM_BRIEF.md` or a data dictionary exists, read it first. **Where the official brief or data dictionary conflicts with this prompt about data fields, the official material wins.** Record the conflict in `DEVELOPMENT_NOTES.md`.
3. Work through the phases in section 17 without waiting for approval. After each phase: run its checks, update `TODO.md`, append decisions/assumptions/blockers to `DEVELOPMENT_NOTES.md`.
4. Do not ask questions unless truly blocked (a credential or file that does not exist and has no fallback). Otherwise take the most conservative assumption, log it under "Assumptions", and continue.
5. Time-box: if the same error survives 3 genuinely different fix attempts, implement the simplest working alternative, log it, and move on. A working end-to-end MVP beats unfinished ambition.
6. Never fake anything (section 2). No hardcoded API responses, no fake integrations.
7. "Done" means you executed it and saw it work (section 16). Do not claim tests passed, pages work, or deployment happened unless you ran it.
8. No secrets in code, logs or git. Use `.env` (commit only `.env.example`).
9. Use current stable versions. If unsure about a library API (Tailwind, Vite, React Router, Recharts, react-leaflet, SQLAlchemy 2.x, scikit-learn), read its docs rather than guessing.

---

## 1. MISSION AND SUCCESS CRITERIA

Build **CrowdWise**: a bus journey planner for Delhi that shows **expected crowdedness next to every route option**, so commuters can choose between the fastest, the least crowded, or a balanced journey.

The organizers' definition of success (paraphrased): a journey planner that shows crowdedness estimates alongside route options; estimates must be grounded in the e-ticketing/ETM data and must hold up when spot-checked against known peak and off-peak patterns.

Organizer data (arrives after registration): about 4–5 weeks of e-ticketing and ETM records covering ticket sales, routes and timestamps, plus route and stop information from Delhi Transport Stack. Until it arrives, build everything on public GTFS + a clearly labelled synthetic ticket simulator, with a one-command swap to the real data.

Hackathon context: team of 2–3; Phase 1 asks for a proposal and a working prototype; shortlisted teams refine in Phase 2; finale 11 Dec 2026. Judges will look at a working prototype, a documented method, and honest validation.

---

## 2. HONESTY AND PROVENANCE RULES (non-negotiable)

**Four data tiers. Every API payload and every UI element showing data must carry its tier.**

| Tier | Meaning |
|---|---|
| `real_public` | Delhi Buses static GTFS (routes, stops, timetable) from Delhi Transport Stack open data |
| `organizer` | ETM / e-ticketing data supplied by the hackathon organizers |
| `demo_synthetic` | Tickets produced by our simulator |
| `estimated` | Anything inferred or modelled (always name the method) |

Rules:
- Until organizer data is loaded, `DATA_MODE=demo`: a persistent top banner ("DEMO MODE: ticket data is simulated"), a "Simulated" chip on every crowd badge, chart and table, and `data_mode` in every API response. Never use wording like "Delhi bus crowd prediction" in demo mode.
- GTFS-derived times are **scheduled (timetable) times**. Never call them actual, measured or live.
- **Ticket counts are not passengers on board.** The ticket data may cover only a fraction of real ridership (organizers have said e-ticketing is a small share of all bus tickets), and free/pass travel may be absent, partial or recorded differently. So the primary output is a **Relative Crowding Index** (0–100, network-relative) + category **Low / Moderate / High** + a **confidence** level. Show an **occupancy %** only when BOTH (a) verified vehicle capacity and (b) a documented expansion factor exist in config. Otherwise hide it and explain why in a tooltip.
- Do not invent alighting counts. Inferred alightings are allowed only as `estimated`, with the method named.
- Do not invent connectivity, capacity, fares or travel times. Missing = `null` plus "Not available".
- Do not hardcode any pass-holder multiplier or "non-ticketed share". Every such factor lives in config with an `assumption: true` flag and is listed on the About page.
- Metrics computed on synthetic data are labelled "demo data, not evidence of real-world accuracy".
- Do not claim deployment until it is deployed and tested.
- Ticket data may contain personal identifiers (card or phone numbers). Drop or one-way hash them at ingestion. Never expose them in any API, log or commit.

---

## 3. INPUTS AND WORKSPACE CONVENTIONS

Check what exists; do not assume.

- `docs/PROBLEM_BRIEF.md`: full text of the official Problem 2 brief (owner pastes it).
- `data/raw/gtfs/`: Delhi Buses static GTFS (zip or `.txt` files: agency, calendar, stops, routes, trips, stop_times; maybe shapes, feed_info). The feed is large (about 124 MB; `stop_times.txt` about 89 MB), so load with explicit dtypes, `usecols` and chunking.
- `data/raw/organizer/`: ETM / e-ticketing CSV/XLSX files and a data dictionary. **Absent at first.**
- If `data/raw/gtfs/` is missing: try the open GTFS listed in the Delhi Transport Stack data catalogue (https://delhi.transportstack.in/data-services). If that needs login or the network is blocked, build from a tiny **fictional** GTFS fixture (clearly labelled FICTIONAL) so the whole system still runs, and record the blocker in `docs/MANUAL_TODO.md`.
- Raw and processed data are never committed (`data/raw/`, `data/processed/` in `.gitignore`). Small demo artifacts (under 20 MB) may be committed so the demo runs after a fresh clone.

---

## 4. STACK (with fallbacks)

- **Frontend:** React + Vite + JavaScript, Tailwind CSS, React Router, Axios, Recharts, Leaflet + react-leaflet with OpenStreetMap tiles (show OSM attribution).
- **Backend:** Python 3.11+, Flask, Flask-CORS, SQLAlchemy 2.x ORM, Pydantic v2 for request validation, python-dotenv, gunicorn for production.
- **ML/data:** pandas, numpy, scikit-learn (RandomForestRegressor), joblib, pyarrow (parquet), PyYAML.
- **Database:** PostgreSQL through SQLAlchemy. `DATABASE_URL` env var. For zero-setup local work default to SQLite using the same models; `docker-compose.yml` provides Postgres. The app and tests must work on both.
- **Testing:** pytest plus `scripts/smoke_test.py` that hits every endpoint.
- Free and open-source only. No paid APIs.

---

## 5. PROJECT STRUCTURE (improve if needed, keep the named ML modules)

```
crowdwise/
├─ AGENTS.md  README.md  TODO.md  DEVELOPMENT_NOTES.md  .env.example  .gitignore  docker-compose.yml
├─ docs/   MASTER_SPEC.md PROBLEM_BRIEF.md METHODOLOGY.md API.md DATA_SWAP.md DATA_DICTIONARY_DEMO.md
│          GTFS_REPORT.md DATA_QUALITY_REPORT.md PROPOSAL.md TECHNICAL_NOTE.md DEMO_SCRIPT.md MANUAL_TODO.md screenshots/
├─ config/ schema_mapping.yaml  crowd.yaml  planner.yaml  capacity_by_bus_type.yaml
├─ data/   raw/gtfs  raw/organizer  demo/  processed/
├─ backend/
│  ├─ run.py  requirements.txt
│  ├─ app/  (config, extensions, models/, routes/, services/, schemas/, utils/)
│  ├─ ml/   data_loader.py preprocessing.py feature_engineering.py train.py predict.py evaluate.py
│  │        load_reconstruction.py sanity_checks.py profile_data.py artifacts/
│  └─ tests/
├─ scripts/ bootstrap.py generate_demo_data.py ingest_gtfs.py swap_data.py retrain.py smoke_test.py doctor.py
└─ frontend/ (src/components, pages, services, hooks, utils, App.jsx)
```

`scripts/bootstrap.py --demo` must be idempotent and do everything: check environment, init DB, ingest GTFS, generate demo tickets, run the pipeline, train, precompute predictions, seed. `scripts/doctor.py` checks Python/Node versions, env vars, DB reachability, data presence and model artifacts, and prints fixes.

---

## 6. STATIC TRANSIT LAYER (real public GTFS)

1. Load GTFS with string dtypes for all IDs; parse `HH:MM:SS` allowing hours above 24 (convert to seconds).
2. Inspect how Delhi encodes direction. Historically, onward and return journeys were split into separate route IDs, and `direction_id` may be absent. Build a canonical **route-direction** key and a human-facing route number from `route_short_name`. Document the rule in `docs/GTFS_REPORT.md`.
3. Map `service_id` to day types **WEEKDAY / SATURDAY / SUNDAY** via `calendar.txt` (and `calendar_dates.txt` if present). If neither exists, treat all trips as daily and log it.
4. A route-direction can have several stop patterns (short-turns, variants). Treat each distinct ordered stop list as a pattern; group by route for analytics; pick the most frequent pattern as canonical for zones and maps.
5. Build compact derived tables (parquet and DB) instead of querying raw `stop_times` at request time:
   - `stops`, `routes`, `route_patterns`
   - `route_stops` (pattern, sequence, stop, cumulative distance, median scheduled offset in seconds from the first stop)
   - `trip_starts` (pattern, day type, start time) so the departure at any stop = trip start + stop offset
   - `supply` (route-direction, day type, hour → number of scheduled trips, median headway)
6. Define **zones** per route-direction: split ordered stops into up to 8 contiguous zones of roughly equal stop count (one zone per stop when a route has 12 stops or fewer). Crowdedness is modelled per zone. State this simplification in the methodology.
7. Write `docs/GTFS_REPORT.md`: counts, orphan references, routes without timetable, data validity dates, direction handling, caveats. Also create `stops` text search (name, fuzzy, case-insensitive) and nearest-stops-by-coordinate (haversine).

---

## 7. TICKET DATA INGESTION (schema-agnostic)

The real ETM / e-ticketing schema is unknown until the organizers' data arrives. Build for both **ticket-level rows** and **pre-aggregated rows** (a `quantity` column).

1. **Profiling:** `backend/ml/profile_data.py` reads any CSV/XLSX in a folder and writes a profile (columns, dtypes, null %, distinct counts, min/max timestamps, samples, per-day volumes) to `docs/DATA_QUALITY_REPORT.md`.
2. **Mapping:** `config/schema_mapping.yaml` maps canonical fields to source columns, with a synonym list for auto-suggestion. Canonical fields: `ticket_id, timestamp, route_id, route_name, trip_id, bus_id, boarding_stop, destination_stop, quantity, fare, ticket_type, payment_mode, bus_capacity`.
   - **Required:** a timestamp and a route identifier. Everything else is optional.
   - Auto-suggest mappings (synonyms + fuzzy match) and write `schema_mapping.generated.yaml`. If a required field cannot be mapped confidently, stop with a clear message listing candidate columns. Never guess silently.
3. **Cleaning** with a logged funnel (rows in, rows dropped and why): parse timestamps robustly (day-first formats, Excel serials, mixed formats; timezone Asia/Kolkata), drop invalid or future dates, remove exact and ID-based duplicates, handle missing values per field (never invent values; keep nulls), drop or hash personal identifiers, normalise ticket types, flag zero/negative fares and quantities.
4. **Route reconciliation:** match ticket routes to GTFS routes (ID, then short name, then normalised text). Report the match rate. Unmatched routes stay in analytics but are excluded from the planner.
5. **Outage detection:** flag days or hours with abnormally low volume (possible device outage) and allow excluding them from training via config.
6. Raw tickets stay in parquet under `data/processed/`. The database stores aggregates only.

---

## 8. CROWD ESTIMATION METHOD

The pipeline auto-selects a **mode** based on available fields and records it in model metadata and on the About page.

- **Mode A: destination observed.** Tickets give boarding and destination stops. Boardings and alightings per stop are exact within the ticket sample. Load after stop k = previous load + boardings − alightings (cumulative form). Label: `estimated passenger flow (ticket sample)`.
- **Mode B: boarding only.** Infer alightings and label them clearly as `estimated`. Implement, in this order: (1) reverse-direction method for balanced round-trip routes (alighting profile at a stop mirrors the boarding profile of the opposite direction); (2) a distance-decay alighting distribution with terminal absorption as fallback. Validate the inference against the synthetic ground truth. Never present Mode B loads as observed.
- **Mode C: no stop information.** Route-level ticket demand per time band only. Label `ticket demand index`, never "load" or "occupancy".

**Load safeguards (A and B):** load never negative; clamp and count violations; load returns to about zero at the terminal; log reconstruction error stats.

**Crowdedness target per cell** (route-direction, zone, date, hour band):
`load_per_trip = estimated flow in the cell ÷ number of scheduled trips in that band`.
Crowdedness is demand divided by supply: ticket volume alone is misleading when frequency differs. Use `trip_starts` from GTFS as the denominator; if a route has no timetable, mark its confidence Low.

**Crowding Index and categories** (all thresholds in `config/crowd.yaml`, flagged as assumptions):
- `crowd_index` = percentile rank (0–100) of predicted `load_per_trip` against the training distribution (the mapping is saved as an artifact).
- Relative categories: Low below P50, Moderate P50–P85, High above P85.
- If and only if `capacity_verified: true` and an `expansion_factor` with a source is set: `occupancy = load_per_trip × expansion_factor ÷ capacity`, with categories Low < 40%, Moderate 40–75%, High ≥ 75%.
- Capacity source priority: capacity column in the ticket data → vehicle roster → `capacity_by_bus_type.yaml` (placeholder values, always `verified: false` until the owner confirms).
- Optionally expose a GTFS-Realtime-style occupancy label mapping (Low ≈ many seats, Moderate ≈ few seats/standing, High ≈ crushed/full) for interoperability.

**Confidence** (High / Medium / Low): based on the number of observed tickets behind the cell family and prediction spread across trees. Low confidence is shown, never hidden.

---

## 9. MACHINE LEARNING PIPELINE

Modules: `data_loader.py, preprocessing.py, feature_engineering.py, train.py, predict.py, evaluate.py` (+ `load_reconstruction.py`, `sanity_checks.py`).

**Dataset grain:** (route-direction, zone, date, hourly band) with `time_band_minutes` configurable (default 60). Keep training under about 3M rows (category dtypes, float32; restrict to routes with enough tickets if needed, and document it).

**Features available at prediction time only:**
- route-direction attributes: direction, zone index and position fraction (0–1), number of stops, route length, scheduled trips in band, median headway
- calendar: hour (raw + sin/cos), day of week, weekend flag, AM/PM peak flags, optional holiday list from config
- **leakage-safe historical aggregates** computed from earlier data only (for training rows use leave-one-week-out; for validation/test use the training window only): route-direction-zone mean load per trip, same by hour, same by day type and hour
- `has_history` flag; missing history falls back to network medians and lowers confidence
- **Do NOT** use "previous load", "previous boardings" or any quantity from the target period itself as features for future predictions. Do not one-hot encode thousands of route IDs.

**Split:** strictly chronological. Roughly: first ~3 weeks train, next ~1 week validation, final ~1 week test (adapt to the actual date range). Add an automated test asserting `max(train_date) < min(val_date) < min(test_date)`. Also run a **leave-routes-out** check to show cold-start behaviour.

**Models:**
1. Baseline B1: historical median by (route-direction, zone, day type, hour) from the training window.
2. Baseline B2: network median by (day type, hour).
3. **RandomForestRegressor** (production model; modest grid with time-ordered CV; `n_jobs=-1`; fixed random seed). A HistGradientBoosting challenger may be reported for comparison only.
4. Prediction intervals from the spread of tree predictions (10th–90th percentile).

**Evaluation (`evaluate.py`):** MAE, RMSE and WAPE on `load_per_trip`; Spearman rank correlation within each hour (ranking quality matters for recommendations); category accuracy, macro-F1 and confusion matrix; interval coverage. Serve RF unless a baseline beats it on validation WAPE by more than 3%; if so, serve the baseline and say so honestly in the model card.

**Sanity-check harness (`sanity_checks.py`):** this directly mirrors the organizers' success criterion. Report PASS / WARN, never silently pass:
1. Weekday AM (07–10) and PM (17–20) network mean crowding exceeds midday (11–15), which exceeds late night (22–05).
2. Weekday peak exceeds Sunday peak at network level (configurable expectation; on real data a contradiction is a WARN for human review, not proof the model is wrong).
3. Directional asymmetry on a sample of radial routes (inbound-heavy AM vs outbound-heavy PM): report, do not assert.
4. Predictions are non-negative, index within 0–100, monotone category mapping.
Results appear on the About page with the data tier.

**Artifacts** in `backend/ml/artifacts/<data_mode>/`: model (`joblib`), percentile mapping, feature list, config snapshot, metrics JSON, model card (`MODEL_CARD.md`), dataset fingerprint (hash, date range, row counts, mode A/B/C). `scripts/retrain.py` retrains from whatever data is currently configured.

**Serving:** never train inside a request. Precompute route-level predictions for every route-direction × day type × hour into `crowd_predictions`. Compute zone/segment-level predictions in a batch for the requested journey (at most a few dozen rows) and cache them.

---

## 10. DATABASE (SQLAlchemy models, indexes, FKs)

`Route`, `Stop`, `RouteStop` (pattern, sequence, distance, offset), `Bus` (capacity nullable, `capacity_source`, `capacity_verified`), `Trip` (scheduled trips/starts), `PassengerLoad` (cell-level reconstructed flow, `method`/mode, ticket count), `CrowdPrediction` (route-direction, zone, day type, hour, index, load per trip, category, confidence, interval, model version, `data_mode`), `TicketAggregate`, `ModelRun` (metrics, mode, dates), `DatasetMeta` (data tier, source, loaded at).

- Capacity supports null/unknown until verified.
- Add indexes on route, stop, day type, hour, and (route-direction, zone).
- The app must **not crash on an empty database**: `/api/health` reports `degraded` with reasons, list endpoints return empty arrays with a hint, planner returns a clear 503 JSON error, frontend shows a setup-instructions empty state.
- Provide schema creation (`flask db`-style or `create_all` plus an Alembic migration), `seed` command, and documented env vars.

---

## 11. BACKEND API (Flask)

Consistent envelope for **every** response:
`{"ok": true, "data": ..., "meta": {"data_mode": "...", "provenance": {...}, "generated_at": "...", "model_version": "..."}}`
Errors: `{"ok": false, "error": {"code": "...", "message": "...", "details": ...}}` with proper HTTP status codes (400 validation, 404 not found, 503 data/model unavailable, 500 unexpected with a safe message). Validate all inputs with Pydantic. Configure CORS from env.

Required endpoints:
- `GET /api/health`
- `GET /api/routes` (search, pagination, filters) · `GET /api/routes/<route_id>` (directions, ordered stops with coordinates, simplified shape, scheduled run time, trips per hour, crowd summary)
- `GET /api/stops` (`q`, `limit`) · `GET /api/stops/nearby?lat&lng&radius`
- `GET /api/crowd/<route_id>` (`direction`, `day_type` → hour × zone matrix)
- `POST /api/predict-crowd` (route, direction, stop or zone, day type or datetime → index, category, confidence, interval, occupancy only if verified)
- `POST /api/journey/plan` (origin and destination as stop ID or lat/lng, departure datetime, `preference` = `fastest | least_crowded | balanced`, optional custom weight)
- `GET /api/analytics/overview` · `/api/analytics/peak-hours` · `/api/analytics/crowded-routes`
- Added: `GET /api/meta` (data mode, provenance, dataset fingerprint, model version/date, mode A/B/C), `GET /api/model/metrics`, `GET /api/validation/sanity`, `GET /api/data-quality`

All endpoints perform real database queries against real tables. Write `docs/API.md` with request/response examples and a Postman-importable collection.

---

## 12. JOURNEY PLANNER

**Inputs:** origin, destination (stop search, nearest stops from a map pick or coordinates), departure datetime, preference.

**Candidate generation (direct routes, MVP):**
1. Origin stop set = nearest K stops within a walking radius (default 500 m); same for destination.
2. For each route pattern containing an origin stop before a destination stop in sequence, build a candidate (keep the best origin/destination stop pair per route).
3. Times (all labelled **scheduled/estimated**): walk = haversine × 1.3 detour ÷ 4.5 km/h; wait = next scheduled departure at the boarding stop after (departure + walk), or half the median headway when no timetable; in-vehicle = scheduled offset difference between boarding and alighting stop; total = walk + wait + in-vehicle + egress walk.
4. Crowd for each candidate = prediction for the ride's zones at the **estimated boarding time** (not the search time). Return both "crowd at your boarding stop" and "peak crowd on your ride", plus a per-zone profile and confidence.
5. Return at most 8 options, deduplicated.

**One-transfer journeys (stretch):** only if GTFS data supports it reliably (shared stop or stops within 300 m, valid scheduled connection, max total time cap). Crowd of a transfer journey = the worse leg. Never fabricate connectivity. If not implemented, state it as a limitation.

**Transparent scoring (config in `planner.yaml`, shown in the UI as "Why this route"):**
- `time_norm = (T − T_fastest) ÷ max(T_fastest, 10 min)`, capped at 1
- `crowd_norm = crowd_index ÷ 100` (absolute scale, so tiny differences are not exaggerated)
- `score = w_time·time_norm + w_crowd·crowd_norm + 0.15·transfers` (lower is better); ties go to the faster option
- Presets: **Fastest** (1.0 / 0.0), **Balanced** (0.5 / 0.5), **Least crowded** (0.2 / 0.8) with a hard constraint: exclude options slower than 1.5 × fastest + 10 minutes, so the "least crowded" pick is never an absurd detour. Also support a custom slider weight.
- Low-confidence crowd estimates use a neutral value and are flagged, never rewarded or punished.
- Each option returns its score breakdown and a one-line reason in plain language.

If no route exists, return a helpful empty result (nearby stops tried, suggestion to widen the radius), not an error.

---

## 13. FRONTEND AND UX

Feels like a real public-transport product, not a student dashboard. Mobile-first and responsive (test at 390 px and 1280 px).

**Design tokens:** background `#F7FAFC`/white; navy `#0B1F3A`; teal `#0FA3A3`; low = green `#22A06B`; moderate = amber `#F5A623`; high = red `#E5484D`. One typeface (self-hosted, e.g. Inter or Plus Jakarta Sans). Subtle motion only. **Crowd level is never colour alone:** always colour + icon + text label (colour-blind safe). Create a simple CrowdWise logo (SVG).

**Global:** top bar with CrowdWise brand and nav; a persistent **demo-mode banner** when `data_mode=demo`; provenance chips ("Timetable: GTFS", "Crowd: Simulated / Organizer ETM", "Estimated"); OSM attribution; loading skeletons, empty states, readable error messages with retry.

**Pages**
- **A. Planner (`/`)**: CrowdWise branding, origin and destination (autocomplete over stops, "pick on map", optional "use my location"), departure date/time, swap button, preference toggle (Fastest / Balanced / Least crowded), search, 3-step "how it works", honest one-paragraph explanation.
- **B. Results (`/results?...`, shareable URL)**: option cards with total time breakdown (walk / wait / ride), crowd badge (index, category, confidence; occupancy % only when verified), recommended badge with "Why this route" popover, side-by-side comparison of the top 3, preference re-sort without refetch, map preview.
- **C. Route details (`/route/:routeId`)**: Leaflet map with route polyline and stops, ordered stop list, direction toggle, crowd by zone (heat strip) for a selected time, hourly crowd chart for weekday vs weekend, scheduled duration, trips per hour.
- **D. Analytics (`/analytics`)**: network crowd by hour (weekday vs weekend), peak-hour analysis, most crowded routes, route comparison (pick 2–3 routes), data coverage panel. Recharts, consistent colours, tooltips.
- **E. About / Methodology (`/about`)**: how load is estimated (modes A/B/C), the ML approach, thresholds and which are assumptions, validation results and sanity-check PASS/WARN list, a clear real/synthetic/estimated table for everything shown, limitations (sample coverage, ticket ≠ passenger, free travel handling, scheduled not live times).

Do not pad the UI with fake statistics. Every number comes from the API.

---

## 14. DEMO DATA (synthetic ticket simulator)

`scripts/generate_demo_data.py` (deterministic seed, CLI flags) creates **clearly labelled synthetic tickets on top of the real GTFS network** (fallback: the fictional fixture). Stamp every file and DB row with `data_tier=demo_synthetic` and write `docs/DATA_DICTIONARY_DEMO.md` with a "SYNTHETIC" header.

- Choose about 40 real routes stratified by length and corridor type.
- 35 consecutive days (Monday start) of weekday, Saturday and Sunday patterns.
- Simulate **passenger-level journeys**: boardings per scheduled trip from base route demand × hour profile (morning peak, steady afternoon, evening peak; flatter weekends) × stop weight (inbound-heavy AM, outbound-heavy PM on radial routes), negative-binomial noise; each passenger picks an alighting stop with distance-decay; boarding capped at crush capacity (left-behind passengers possible).
- Because journeys are simulated, store **ground-truth loads** per trip and segment (`truth_loads_demo.parquet`). Use it to verify the reconstruction algorithm (Mode A exactly, Mode B approximately) and to prove load conservation. Never report this as real accuracy.
- Emit ETM-like tickets with a configurable **sample coverage** (default 35%) and ticket types, with columns like: `ticket_id, timestamp, route_id, route_short_name, trip_id, vehicle_id, boarding_stop_id, destination_stop_id, fare, ticket_type, payment_mode`.
- Two variants via `--variant with_destination | boarding_only` (default `with_destination`); tests must exercise both.
- Vehicle roster with demo-assumed capacities (`verified: false`). In demo mode the UI may show occupancy labelled "Simulated occupancy". In organizer mode, only if verified.
- `scripts/swap_data.py --path data/raw/organizer --mode organizer`: profile the files, suggest the mapping, stop for review only if a required field is ambiguous, otherwise run cleaning → reconstruction → training → precompute → switch `DATA_MODE` to `organizer` → regenerate `DATA_QUALITY_REPORT.md` and the model card. Document in `docs/DATA_SWAP.md` (under one page, step by step).

---

## 15. TESTING

Automated (pytest, SQLite-backed, small deterministic fixtures including a tiny GTFS):
- schema mapping (synonyms, ambiguity stops), timestamp parsing, cleaning funnel, duplicate removal, PII dropping
- load reconstruction: conservation, non-negative, terminal ≈ 0, Mode A recovers truth, Mode B within tolerance, Mode C never emits "load"
- **no-leakage tests:** chronological split assertion; historical-aggregate features never use rows from the row's own or later period
- feature availability test: the feature list contains no target-period quantities
- baseline vs RF evaluation runs and metrics are finite
- scoring function (presets, hard constraint, ties, single candidate, low-confidence handling)
- planner on the tiny GTFS fixture (direct route found, wrong-direction route rejected)
- API contract tests for every endpoint (success, 400, 404) and **empty-database** behaviour
- provenance: every response carries `data_mode`; demo mode never omits the "Simulated" flag

---

## 16. VERIFICATION LOOP (you must actually run this)

1. Install backend and frontend dependencies.
2. `python scripts/bootstrap.py --demo` end to end (DB init, GTFS ingest, demo data, pipeline, training, precompute, seed).
3. Run `pytest`; fix all failures.
4. Start backend and frontend; run `scripts/smoke_test.py` against every endpoint.
5. Use the browser agent to drive the full journey: planner → results → switch preference → route details → analytics → about. Capture screenshots into `docs/screenshots/`. Check the browser console and network tab for errors; fix them. Confirm displayed numbers match raw API responses. Repeat at a mobile viewport (390 px).
6. Empty-state test: start with an empty DB and with a missing model file; confirm graceful behaviour.
7. Re-run the whole loop after the last fix. Record the final results (what passed, what is WARN) in `DEVELOPMENT_NOTES.md`.

---

## 17. PHASES AND DELIVERABLES

- **P0 Setup:** inputs check, `docs/MASTER_SPEC.md`, `AGENTS.md`, plan, scaffold, `TODO.md`.
- **P1 Static layer:** GTFS ingest, compact tables, zones, stop search, `GTFS_REPORT.md`, tests.
- **P2 Data pipeline:** demo simulator, profiling, mapping, cleaning, route reconciliation, reconstruction modes, tests.
- **P3 ML:** dataset build, baselines, RF, evaluation, sanity harness, artifacts, precompute, retrain script, tests.
- **P4 Backend:** DB models, services, endpoints, planner, scoring, tests.
- **P5 Frontend:** all five pages on real API data, states, responsive layout.
- **P6 Integration and verification loop** (section 16).
- **P7 Docs and submission pack, deployment prep.**

**Final deliverables:**
1. Working React frontend and Flask backend, PostgreSQL-ready SQLAlchemy models (SQLite fallback)
2. Data pipeline with schema mapping and a one-command data swap
3. Baseline and Random Forest models, evaluation, sanity-check report, model card, retrain script
4. Prediction APIs and a functional journey planner with transparent scoring
5. Analytics dashboard and About/Methodology page
6. Synthetic demo dataset with ground truth, clearly labelled and separate from real data
7. Automated tests plus smoke test
8. `README.md` (setup and run, env vars, API summary), `.env.example`, `docs/API.md`, `docs/DATA_SWAP.md`
9. `docs/PROPOSAL.md` (about 2 pages: problem understanding, approach, data, model, planner, validation plan, limitations, roadmap)
10. `docs/TECHNICAL_NOTE.md` (about 3 pages: methodology and validation, honest about limits)
11. `docs/DEMO_SCRIPT.md` (3-minute video script with exact clicks and talking points, plus a 6-slide pitch outline)
12. Deployment prep: production env vars, CORS, gunicorn config, build instructions for Vercel (frontend), Render or similar (backend) and hosted Postgres/Supabase, health check. **Do not claim deployment is done.**
13. `docs/MANUAL_TODO.md`: the exact list of everything that still needs the owner, each with step-by-step instructions and a workaround where possible (registration, official data files, data dictionary, capacity confirmation, expansion factor, accounts for deployment, demo video recording, final proposal submission)
14. `TODO.md` and `DEVELOPMENT_NOTES.md` kept current

---

## 18. DEFINITION OF DONE

- [ ] Fresh clone + `python scripts/bootstrap.py --demo` + start commands gives a working app
- [ ] All five pages work with real API data; no console errors; mobile layout verified
- [ ] Every crowd value on screen shows its provenance; demo banner visible in demo mode
- [ ] Planner returns multiple real options, supports all three preferences, explains its choice
- [ ] RF vs baselines compared on a chronological test set; sanity checks reported honestly
- [ ] No leakage tests pass; no personal identifiers anywhere
- [ ] Empty DB and missing-model scenarios degrade gracefully
- [ ] `swap_data.py` tested end to end using the simulator's output as a stand-in "organizer" file with different column names
- [ ] Docs complete; `MANUAL_TODO.md` lists exactly what the owner must do

Begin with P0 now. Do not stop at planning. Continue autonomously through P7 and finish with a short final report (what works, what is demo-only, what needs the owner).
