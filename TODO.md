# TODO.md — CrowdWise Phase Tracker

## Phase R0: Safety & Real Dataset Inventory
- [x] Create git safety point and branch
- [x] Locate official organizer datasets (`October-Delhi.csv` and `data/raw/gtfs/`)
- [x] Profile datasets and create `docs/DATASET_INVENTORY.md`
- [x] Document schemas, null percentages, 5 sample masked rows, and assumptions

## Phase R1: Purge Everything Synthetic
- [x] Delete `scripts/generate_demo_data.py`, `data/synthetic/`, and demo truth files
- [x] Purge demo models and drop/recreate database schemas
- [x] Refactor `scripts/bootstrap.py` to require real organizer data (fails cleanly if missing)
- [x] Change active data mode to `data_mode = 'organizer'` with `organizer` / `real_public` / `estimated` tiers
- [x] Update top banner to factual provenance banner with October 2026 date range

## Phase R2: Real Data Processing Pipeline
- [x] Ingest official Delhi static GTFS (6,862 stops, 2,574 routes, 3,498 patterns, 109,660 pattern stops)
- [x] Build vectorized ingestion engine in `scripts/process_october_tickets.py` ($O(1)$ token hashing)
- [x] Process all 2,559,899 ETM tickets across all 31 days of October 2026
- [x] Reconstruct 3,322,312 corridor zone demand facts in `staging_zone_loads.parquet` and SQLite
- [x] Implement Mode A exact O-D (77.3% match) + Mode B reverse/decay inference (11.1% match)
- [x] Apply Pink Pass expansion factor ($\gamma_r = 1.30$) for non-ticketed female travel
- [x] Materialize fast query tables `fact_daily_summary` and `fact_hourly_summary`
- [x] Publish `docs/DATA_QUALITY_REPORT.md` and `/api/data-quality`

## Phase R3: Retrain ML Models on Real Demand Facts
- [x] Implement chronological split (Train: Oct 1–21 [70%], Val: Oct 22–25 [15%], Test: Oct 26–31 [15%])
- [x] Train baseline `HistoricalMeanRegressor` and production `RandomForestRegressor` (34.4 MB)
- [x] Calibrate Relative Crowding Index (RCI 0–100) and 3-tier comfort categories
- [x] Verify evaluation metrics: Category Accuracy = 99.30%, Spearman $\rho = 0.6879$, WAPE = 55.46%, MAE = 1.38 pass.
- [x] Pass transit domain sanity-check harness (100% PASS: AM Peak ratio 2.84x, PM Peak 2.48x)
- [x] Publish `docs/MODEL_CARD.md`
- [x] Create idempotent rebuild script `scripts/rebuild_from_real_data.py`

## Phase R4: Database & API Hardening
- [x] Seed SQLite database (`backend/crowdwise.db`) with 3.32M facts and GTFS schedules
- [x] Reconcile row counts: 2.56M tickets $\rightarrow$ 3.32M zone facts
- [x] Expose `/api/health`, `/api/meta`, `/api/data-tier`, `/api/data-quality`, `/api/model/metrics`, `/api/validation/sanity`
- [x] Standardize JSON envelope with execution timing and degradation safety

## Phase R5: Web Application Polish
- [x] Update `PlannerPage.jsx` with autocomplete, GTFS stops, and 3 routing presets
- [x] Update `ResultsPage.jsx` with multi-option comparison and RCI badges
- [x] Update `RouteDetailsPage.jsx` with Leaflet route shapes and 24h hourly profiles
- [x] Update `AnalyticsPage.jsx` with 31-day volume timeseries, diurnal curves, top corridors, and takeaway sentences
- [x] Update `AboutPage.jsx` with full methodology, data tiers, cleaning funnel, and DPDP disclosures
- [x] Replace demo banner with factual organizer ETM banner in `DemoBanner.jsx`

## Phase R6: Verification & Testing
- [x] Create standalone reconciliation script `scripts/reconcile_raw_data.py`
- [x] Audit 5 busy and 5 quiet routes directly from raw CSV; publish `docs/VALIDATION_REPORT.md`
- [x] Run `python scripts/smoke_test.py` (9/9 PASS)
- [x] Run `python scripts/verify_full_website.py` (10/10 PASS)
- [x] Run pytest suite (`python -m pytest tests/e2e/`) (348/348 PASS)
- [x] Run domain sanity checks (`python scripts/run_sanity_checks.py`) (100% PASS)

## Phase R7: Documentation & Hackathon Submission Pack
- [x] Update `README.md` with real metrics, quickstart, and rebuild commands
- [x] Update `docs/DEMO_SCRIPT.md` (3-minute timed script with exact clicks and talking points)
- [x] Update `docs/PROPOSAL.md` and `docs/PROPOSAL.html`
- [x] Update `docs/TECHNICAL_NOTE.md` and `docs/TECHNICAL_NOTE.html`
- [x] Update `docs/MANUAL_TODO.md` with video recording and submission guidelines
- [x] Clean commit history and push to GitHub remote
