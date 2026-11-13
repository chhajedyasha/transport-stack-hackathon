# ARCH.md — CrowdWise Architecture Specification

## 1. System Overview
CrowdWise is a crowdedness-aware bus journey planner for Delhi (Transport Stack Hackathon 2026, Problem 2). It combines public GTFS static transit schedules with electronic ticketing machine (ETM) telemetry to forecast load per scheduled trip and present trade-offs between travel time and crowding.

```
                              +------------------------------------+
                              |     Delhi Transport Stack (DTS)    |
                              |  - GTFS Static (DLM1: 10.5k stops) |
                              |  - ETM Telemetry / Synthetic Feed  |
                              +-----------------+------------------+
                                                |
                                                v
+---------------------------------------------------------------------------------------------------+
| 1. Static Transit & Storage Layer                                                                 |
|  - Derived tables: dim_stops, dim_routes, dim_route_patterns, rel_pattern_stops, fact_route_supply|
|  - Directionality: 4-level fallback (explicit direction_id -> UP/DOWN regex -> trip ID -> bearing)|
|  - 8-Zone Sequence Partitioning: zone_id = min(7, floor(8 * stop_seq / total_stops))              |
|  - Multi-Modal Spatial Search: Exact, Trigram Fuzzy Levenshtein (>=0.45), cKDTree Spatial (<0.2ms)|
+-----------------------------------------------+---------------------------------------------------+
                                                |
                                                v
+---------------------------------------------------------------------------------------------------+
| 2. ETM Ingestion & Demand Reconstruction                                                          |
|  - Mode A: Exact boardings & alightings when destination stop is recorded                         |
|  - Mode B: Boardings only -> Inferred alightings via reverse-route mirroring + distance decay      |
|  - Mode C: Route-level volume disaggregation across zones                                         |
|  - DPDP Compliance: HMAC-SHA-256 pseudonymization of ticket/card identifiers                      |
|  - Data Swap Engine (scripts/swap_data.py): One-command transition from demo to real ETM data     |
+-----------------------------------------------+---------------------------------------------------+
                                                |
                                                v
+---------------------------------------------------------------------------------------------------+
| 3. Machine Learning & Estimation Layer                                                            |
|  - Grain: (route_id, direction_id, zone_id, day_type, hour)                                       |
|  - Target: load_per_trip = estimated_flow_in_cell / scheduled_trips_in_band                       |
|  - Split: Chronological Invariant (max(train) < min(val) < min(test)) — No Target Leakage         |
|  - Models: HistoricalMeanRegressor (Baseline B1/B2) vs RandomForestRegressor (Production)         |
|  - Uncertainty & Confidence: Inter-tree prediction spread (10th-90th percentile) -> High/Med/Low  |
|  - Sanity Harness: Automated validation of AM/PM peak vs midday vs night crowding                |
+-----------------------------------------------+---------------------------------------------------+
                                                |
                                                v
+---------------------------------------------------------------------------------------------------+
| 4. Journey Planning & Backend API (Flask + SQLAlchemy)                                             |
|  - Response Envelope: { ok: bool, data: ..., error: null|..., meta: { data_tier, ... } }          |
|  - Candidate Generator: Origin & Dest stops within 500m radius -> Direct pattern matches           |
|  - Scheduled Times: Walk (haversine * 1.3 / 4.5kmh) + Wait (scheduled next / 0.5 headway) + Ride   |
|  - Multi-Objective Scoring:                                                                       |
|      time_norm = (T - T_fastest) / max(T_fastest, 10 min)                                         |
|      crowd_norm = crowd_index / 100                                                               |
|      score = w_time * time_norm + w_crowd * crowd_norm                                            |
|      Presets: Fastest (1.0/0.0), Balanced (0.5/0.5), Least Crowded (0.2/0.8 with 1.5x detour cap) |
|  - Resilience: Graceful degraded state (empty array + setup hint) on empty DB or missing model    |
+-----------------------------------------------+---------------------------------------------------+
                                                |
                                                v
+---------------------------------------------------------------------------------------------------+
| 5. Frontend UI/UX (React 18 + Vite + Tailwind CSS)                                                |
|  - 5 Core Pages:                                                                                  |
|      / (Planner) -> Autocomplete, map picker, preference toggle                                   |
|      /results -> Option cards, time breakdown, RCI badges, side-by-side comparison                |
|      /route/:id -> Interactive Leaflet polyline with 8-zone heat strip, 24h hourly profiles       |
|      /analytics -> System peak hours, most crowded routes, multi-route corridor comparison        |
|      /about -> Methodology, assumptions, sanity check scorecard, data tier transparency           |
|  - Accessibility: Color-blind safe (badge color + text label + icon), responsive (390px to 1280px)|
|  - Provenance Banner: Persistent demo badge when data_mode=demo                                   |
+---------------------------------------------------------------------------------------------------+
```

## 2. Directory Layout
```
crowdwise/
├── AGENTS.md                  # Autonomy and governance rules
├── README.md                  # Setup and execution guide
├── TODO.md                    # Live progress tracker
├── DEVELOPMENT_NOTES.md       # Decision log and assumptions
├── docker-compose.yml         # Optional PostgreSQL service
├── .env.example               # Template environment variables
├── config/
│   ├── crowd.yaml             # Crowding thresholds & capacity multipliers
│   ├── planner.yaml           # Journey scoring weights & walking limits
│   └── schema_mapping.yaml    # ETM to canonical column mappings
├── data/
│   ├── raw/gtfs/              # Static GTFS feeds (zip / text)
│   ├── raw/organizer/         # Real organizer ETM drops
│   ├── demo/                  # Synthetic demo dataset
│   └── processed/             # Parquet derived tables
├── backend/
│   ├── run.py                 # Development runner
│   ├── requirements.txt       # Python dependencies
│   ├── app/
│   │   ├── __init__.py        # Flask application factory
│   │   ├── config.py          # App configuration
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── routes/            # Blueprint endpoints
│   │   ├── services/          # Business logic (GTFS, ETM, ML, Planner)
│   │   └── utils/             # Helpers (spatial, math, time)
│   ├── ml/
│   │   ├── data_loader.py     # Schema ingestion
│   │   ├── load_reconstruction.py # Modes A, B, C reconstruction
│   │   ├── feature_engineering.py # Leakage-safe features
│   │   ├── train.py           # Model training
│   │   ├── evaluate.py        # Evaluation metrics
│   │   └── sanity_checks.py   # Peak/off-peak validation harness
│   └── tests/                 # Automated test suite
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx            # Main app router
│       ├── components/        # Reusable UI components
│       ├── pages/             # 5 core pages
│       └── services/          # API client
├── scripts/
│   ├── bootstrap.py           # One-command full system setup (--demo)
│   ├── generate_demo_data.py  # Synthetic ticket simulator
│   ├── ingest_gtfs.py         # GTFS table generator
│   ├── swap_data.py           # Live data swap utility
│   ├── retrain.py             # Retraining trigger
│   ├── smoke_test.py          # End-to-end API smoke test
│   └── doctor.py              # Environment and dependency checker
└── docs/
    ├── MASTER_SPEC.md         # Full prompt verbatim
    ├── ARCH.md                # System architecture (this document)
    ├── DESIGN.md              # UI/UX and data design
    ├── MANUAL_TODO.md         # Manual owner tasks checklist
    ├── PROPOSAL.md            # Hackathon proposal document
    ├── TECHNICAL_NOTE.md      # Technical methodology note
    └── DEMO_SCRIPT.md         # Video walkthrough & pitch script
```

