# Project: CrowdWise (Transport Stack Hackathon 2026 Problem 2)

## Architecture
CrowdWise is a bus journey planner for Delhi that estimates and visualizes expected bus crowdedness next to every route option, empowering commuters to choose between the fastest, the least crowded, or a balanced journey.

### High-Level System Architecture
```
                                  +------------------------------------+
                                  |     Delhi Transport Stack (DTS)    |
                                  |  - GTFS Static (DLM1: 10.5k stops) |
                                  |  - ETM Telemetry / Synthetic Feed  |
                                  +-----------------+------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
| Data Pipeline & Storage Layer                                                                     |
|  - GTFS Ingestion: dim_stops, dim_routes, dim_route_patterns, rel_pattern_stops, fact_route_supply |
|  - 8-Zone Sequence Partitioning: zeta(s, N) = min(7, floor(8s / N))                               |
|  - Multi-Modal Stop Search: Exact, Prefix, Trigram Fuzzy Levenshtein (>=0.45), cKDTree Spatial    |
|  - ETM Ingestion: Mode A (O-D known), Mode B (Alighting Inference via Reverse + Decay), Mode C    |
|  - Synthetic Simulator: scripts/generate_demo_data.py -> demo_tickets.parquet & truth_loads.parquet|
|  - Data Swap Engine: scripts/swap_data.py with HMAC-SHA-256 PII stripping / pseudonymization      |
+---------------------------------------------------+-----------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
| Machine Learning & Estimation Layer                                                               |
|  - Chronological Invariant Split: max(train) < min(val) < min(test) (70 / 15 / 15)                |
|  - Historical Baseline (HistoricalMeanRegressor) vs. RandomForestRegressor (variance confidence)  |
|  - Metrics: Finite MAE, RMSE, WAPE (sum|y-y^|/sum y), Spearman Rank Correlation                   |
|  - Relative Crowding Index (RCI 0-100) & Categories: Low (<40), Moderate (40-70), High (>70)     |
|  - Peak / Off-Peak Sanity Harness: Peak >= 1.25 * Midday > Night on Weekdays                      |
+---------------------------------------------------+-----------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
| Journey Planner & Backend REST API (Flask + SQLAlchemy)                                            |
|  - Envelope: { ok, data, error, meta: { version, data_tier, timestamp, execution_time_ms } }       |
|  - Provenance Tiers: real_public, organizer, demo_synthetic, estimated                            |
|  - Journey Scoring: Score = w_time * (T/T_bar) + w_crowd * (C_journey/100) + w_wait * (T_wait/T_bar)|
|  - Presets: fastest (1.0/0.0), balanced (0.5/0.5), least_crowded (0.2/0.8)                        |
|  - Constraints: Max Detour ratio <= 2.8, Top 8 Deduplicated Options                               |
|  - Graceful Degradation: HTTP 200 with structured empty/fallback state on unseeded DB/missing model|
+---------------------------------------------------+-----------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------+
| Frontend Application (React 18 + Vite + Tailwind CSS)                                             |
|  - 5 Core Routes: / (Planner), /results (Comparison), /route/:routeId (Leaflet Map + 24h Charts),  |
|                   /analytics (Corridor Crowding Heatmaps), /about (Methodology & Data Tiers)      |
|  - Persistent Demo Banner (data_mode=demo) & Simulated Badges on synthetic metrics                |
|  - Leaflet GPS Polylines (GTFS shapes.txt) with 8-Zone color-coded corridor shading               |
+---------------------------------------------------------------------------------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | GTFS Static Ingestion | Ingest Delhi Buses GTFS static zip (10,559 stops, 2,403 routes) into compact tables | M1 | Survey / R1 |
| F02 | Route Directionality Resolution | 4-level resolution hierarchy (explicit direction_id -> regex name UP/DOWN -> trip_id -> bearing) | M1 | Survey / R1 |
| F03 | Day Type Mapping | Map calendar.txt 7-day service schedule into WEEKDAY, SATURDAY, SUNDAY | M1 | Survey / R1 |
| F04 | Contiguous 8-Zone Partitioning | Closed-form partition formula min(7, floor(8s/N)) for route corridor modeling | M1 | Survey / R1 |
| F05 | Multi-Modal Stop Search | Exact, prefix, trigram fuzzy Levenshtein (>=0.45), and cKDTree spatial nearest (<0.2ms) | M1 | Survey / R1 |
| F06 | ETM Schema-Agnostic Ingestion | Ingest and profile conductor ETM logs across multiple formats | M2 | Survey / R2 |
| F07 | Mode A Demand Reconstruction | Boarding & destination known direct O-D matrix construction | M2 | Survey / R2 |
| F08 | Mode B Alighting Inference | Hybrid reverse-direction + exponential distance-decay alighting probability model | M2 | Survey / R2 |
| F09 | Mode C Demand Disaggregation | Route-level aggregate demand disaggregation across zones | M2 | Survey / R2 |
| F10 | Synthetic Ticket Simulator | scripts/generate_demo_data.py generating demo_tickets.parquet & truth_loads_demo.parquet | M2 | Survey / R2 |
| F11 | One-Command Data Swap Engine | scripts/swap_data.py with 9-step atomic staging, retraining trigger, and rollback | M2 | Survey / R2 |
| F12 | Privacy Engine & PII Salting | Drop or hash personal identifiers via HMAC-SHA-256 (DPDP Act 2023 compliant) | M2 | Survey / R2 |
| F13 | Chronological Split Invariant | Automated leakage assertion max(train_date) < min(val_date) < min(test_date) (70/15/15) | M3 | Survey / R3 |
| F14 | Baseline Regressor | HistoricalMeanRegressor historical time-window baseline | M3 | Survey / R3 |
| F15 | Random Forest Regressor | RandomForestRegressor with tree variance estimation for confidence intervals | M3 | Survey / R3 |
| F16 | Model Evaluation Suite | Finite MAE, RMSE, WAPE, and Spearman rank correlation | M3 | Survey / R3 |
| F17 | Relative Crowding Index (RCI) | 0–100 index calibrated to 60-passenger capacity into Low (<40), Mod (40-70), High (>70) | M3 | Survey / R3 |
| F18 | Peak/Off-Peak Sanity Harness | Peak >= 1.25 * Midday > Night on weekdays without silent failures | M3 | Survey / R3 |
| F19 | Direct Route Journey Planner | Match direct route patterns where origin_seq < dest_seq with max 8 deduplicated options | M4 | Survey / R4 |
| F20 | Travel & Wait Time Estimation | Scheduled trip duration and headway-based wait time estimation (T_wait = 0.5 * headway) | M4 | Survey / R4 |
| F21 | Multi-Objective Scoring Presets | Transparent weighting: fastest (1.0/0.0), balanced (0.5/0.5), least_crowded (0.2/0.8) | M4 | Survey / R4 |
| F22 | Max Detour Constraint Filter | Filter out circuitous routes with detour ratio delta = D_transit / D_straight > 2.8 | M4 | Survey / R4 |
| F23 | Flask API & Dialect-Agnostic ORM | Dual-dialect SQLite / PostgreSQL SQLAlchemy models and standard envelope | M4 | Survey / R4 |
| F24 | Graceful Degradation Engine | Return structured 200 OK responses with empty state on unseeded DB / missing model | M4 | Survey / R4 |
| F25 | Frontend Planner Page (/) | Mobile-first origin/destination stop search, date-time selector, preference toggle | M5 | Survey / R5 |
| F26 | Frontend Results Page (/results) | Multi-option comparison cards, RCI badges, time vs crowding trade-off differentials | M5 | Survey / R5 |
| F27 | Frontend Route Details (/route/:id) | Leaflet polyline with 8-zone shaded corridor, 24-hour hourly crowding chart | M5 | Survey / R5 |
| F28 | Frontend Analytics Page (/analytics) | System-wide busiest routes, peak hour distribution, corridor heatmaps | M5 | Survey / R5 |
| F29 | Frontend About Page (/about) | Data tier disclosures, methodology, alighting inference math, DPDP compliance | M5 | Survey / R5 |
| F30 | Hackathon Documentation & Bootstrap | MASTER_SPEC.md, AGENTS.md, MANUAL_TODO.md, proposal, tech note, demo script, bootstrap.py, smoke_test.py | M5 | Survey / R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Dual-Track E2E Testing Track | Requirement-driven opaque-box test harness & test suite (Tiers 1-4) | None | IN_PROGRESS |
| M1 | Static Transit Layer & Ingestion | GTFS ingestion, compact tables, directionality, 8-zone partition, stop search | None | PLANNED |
| M2 | Data Pipeline & Demand Reconstruction | ETM pipeline modes A/B/C, synthetic simulator, truth loads, swap script, PII hashing | M1 | PLANNED |
| M3 | ML & Crowdedness Estimation | Chronological split, baseline & Random Forest, RCI 0-100, sanity check harness | M1, M2 | PLANNED |
| M4 | Journey Planner & Backend API | Flask REST API, SQLAlchemy ORM, multi-objective scoring, detour filter, envelope | M1, M3 | PLANNED |
| M5 | Frontend & Documentation Pack | React+Vite+Tailwind 5 pages, Leaflet maps, bootstrap script, smoke test, docs pack | M4 | PLANNED |
| M-Final | Final Milestone: 100% E2E Pass & Hardening | Pass 100% E2E test suite (Tiers 1-4) & adversarial hardening (Tier 5) | M0, M5 | PLANNED |

## Interface Contracts

### M1 ↔ M2 (Transit Layer to Data Pipeline)
- `dim_stops`: `stop_id (str), stop_code (str), stop_name (str), stop_lat (float), stop_lon (float)`
- `dim_route_patterns`: `pattern_id (str), route_id (str), direction_id (int: 0/1), num_stops (int), total_dist_km (float)`
- `rel_pattern_stops`: `pattern_id (str), stop_sequence (int), stop_id (str), zone_id (int: 0-7), dist_km (float)`
- Function `get_stop_sequence(pattern_id: str) -> List[Tuple[int, str, int]]` (seq, stop_id, zone_id)
- Function `resolve_direction(route_name: str, trip_id: str) -> int` (0 for UP/outbound, 1 for DOWN/inbound)

### M2 ↔ M3 (Data Pipeline to ML Modeling)
- Output Parquet Schema `truth_loads_demo.parquet` / `zone_hourly_loads.parquet`:
  `route_id (str), direction_id (int), zone_id (int: 0-7), day_type (str: WEEKDAY/SATURDAY/SUNDAY), hour (int: 0-23), trip_date (date), mean_load (float), trip_count (int)`
- Function `load_training_dataset(data_path: str) -> pd.DataFrame`
- Invariant: `max(df_train['trip_date']) < min(df_val['trip_date']) < min(df_test['trip_date'])`

### M3 ↔ M4 (ML Estimation to Journey Planner & API)
- Model Artifact: `models/random_forest_regressor.pkl` (or pipeline) + `models/baseline_regressor.pkl` + `models/metadata.json`
- Function `predict_crowding(route_id: str, direction_id: int, zone_id: int, day_type: str, hour: int) -> Dict[str, Any]`:
  Returns: `{ 'load': float, 'rci': float (0-100), 'category': 'Low'|'Moderate'|'High', 'confidence': 'low'|'medium'|'high', 'tier': 'estimated' }`
- Fallback heuristic on missing model: Return historical/baseline estimate or null with explanatory flag without error.

### M4 ↔ M5 (Backend API to Frontend)
- Base URL: `http://localhost:5000/api`
- Envelope:
  ```json
  {
    "ok": true,
    "data": { ... },
    "error": null,
    "meta": {
      "version": "1.0.0",
      "data_tier": "demo_synthetic" | "real_public" | "organizer" | "estimated",
      "timestamp": "2026-11-13T14:30:00Z",
      "execution_time_ms": 42.5
    }
  }
  ```
- Endpoints:
  - `GET /api/health`
  - `GET /api/stops/search?q=...&lat=...&lon=...`
  - `POST /api/journey/plan` -> payload `{ origin_stop_id, destination_stop_id, departure_time, day_type, preference: 'fastest'|'balanced'|'least_crowded' }`
  - `GET /api/routes/:routeId` -> route details, stops with zone IDs, shape polyline coords, 24h hourly crowding profiles
  - `GET /api/analytics/summary` -> system metrics, top 5 busiest routes, peak hour distribution
  - `GET /api/data-tier` -> current runtime data mode (`data_mode=demo` or `organizer`)

## Code Layout
```
c:\Users\rajsi\OneDrive\Desktop\Documents\raj\transport  hackathon\crowdwise\
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask factory, CORS, blueprints, error handlers
│   │   ├── config.py            # SQLite/PostgreSQL config, data tier flags
│   │   ├── models/              # SQLAlchemy ORM models (dim_stops, dim_routes, etc.)
│   │   │   ├── __init__.py
│   │   │   └── transit.py
│   │   ├── services/            # Core business logic
│   │   │   ├── gtfs_service.py  # GTFS parser & spatial search (cKDTree)
│   │   │   ├── etm_service.py   # Demand reconstruction & alighting inference
│   │   │   ├── ml_service.py    # Predictor wrapper & RCI mapper
│   │   │   └── planner_service.py # Direct route search & multi-objective scoring
│   │   └── routes/              # Flask blueprint route handlers
│   │       ├── health.py
│   │       ├── stops.py
│   │       ├── journey.py
│   │       ├── routes.py
│   │       └── analytics.py
│   ├── run.py                   # Development server entry point
│   └── tests/                   # Pytest suite
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx              # Router & layout with persistent demo banner
│       ├── main.jsx
│       ├── components/          # Reusable UI (StopSelector, RouteCard, LeafletMap, HourlyChart)
│       ├── pages/               # Planner, Results, RouteDetails, Analytics, About
│       └── services/            # API client with data tier extraction
├── data/
│   ├── gtfs/                    # Raw static GTFS zip / extracted txt files
│   ├── synthetic/               # Synthetic tickets & truth loads
│   └── organizer/               # Organizer ETM drop location
├── models/                      # Trained model pickle files & metadata
├── scripts/
│   ├── bootstrap.py             # One-command end-to-end setup (--demo)
│   ├── generate_demo_data.py    # Synthetic ticket simulator with ground truth
│   ├── train_models.py          # Chronological split & model trainer
│   ├── swap_data.py             # One-command data swap script
│   └── smoke_test.py            # Full API integration smoke test
└── docs/
    ├── MASTER_SPEC.md           # Master specification
    ├── AGENTS.md                # Autonomy & agent rules
    ├── MANUAL_TODO.md           # Manual owner action checklist
    ├── PROPOSAL.md              # Hackathon proposal
    ├── TECHNICAL_NOTE.md        # Technical methodology note
    └── DEMO_SCRIPT.md           # Video / presentation walkthrough
```
