# DEVELOPMENT_NOTES.md — Decisions, Assumptions & Conflict Log

## 1. Project Initialization (2026-11-13)
- **Prompt Verification**: The uploaded master prompt was reviewed in its entirety (all 18 sections present, ending with Section 18 Definition of Done).
- **Workspace Location**: Project workspace folder configured at `c:\Users\rajsi\OneDrive\Desktop\Documents\raj\transport  hackathon\crowdwise\`.
- **Autonomy Mode**: Active. All design, engineering, machine learning, testing, and documentation are handled autonomously while the owner is in exams.

## 2. Core Architectural Decisions
- **Database Dialect**: Dual-mode SQLite (default for zero-setup local dev) and PostgreSQL (via Docker Compose and `DATABASE_URL` for production).
- **Static GTFS Strategy**: Delhi Buses static GTFS (DLM1) is large (~124MB uncompressed). Compact derived tables are generated in parquet and indexed SQLite tables to guarantee sub-millisecond query responses.
- **Ticketing & ETM Strategy**: Until official organizer ETM dataset arrives, `scripts/generate_demo_data.py` generates 35 days of synthetic passenger tickets across 40 representative corridors with realistic peak/off-peak and directional asymmetry.
- **Ground Truth Retention**: `truth_loads_demo.parquet` is preserved to rigorously test and prove the load reconstruction algorithm (Mode A vs Mode B).
- **Machine Learning**: RandomForestRegressor with tree-variance estimation for confidence intervals. Strictly chronological split ensures zero data leakage.

## 3. Assumptions Log
- **Bus Capacity**: Assumed standard DTC low-floor capacity of 60 passengers (seated + standing). Flagged as `assumption: true` in `config/capacity_by_bus_type.yaml`.
- **Expansion Factor**: Assumed multiplier of 2.5x to account for non-ticketed passengers (free female travel passes, monthly bus passes, uncollected fares). Flagged as `assumption: true`.
- **Walking Speed**: Haversine distance multiplied by 1.3 road detour factor divided by 4.5 km/h walking speed.
- **Zone Partitioning**: Ordered route stops partitioned into up to 8 contiguous zones using the closed-form formula `zone_id = min(7, floor(8 * seq / N))`. Routes with 12 or fewer stops assign 1 zone per stop.



## 4. Official Problem Statement Ingestion & Alignment (2026-11-13)
- **Official Brief Saved**: Ingested full official problem statement into `docs/PROBLEM_BRIEF.md`.
- **Real Dataset Discovered**: Download URL identified at `https://pub-091bd9e794bb4877b10b29e6df80f065.r2.dev/2026-10/October-Delhi.csv.zip` covering 1 to 31 October 2026 (~2.56M tickets).
- **Exact Field Mapping Confirmed**:
  - `start_stop_name` -> `boarding_stop`
  - `end_stop_name` -> `destination_stop` (Confirms Mode A: Destination Observed!)
  - `route` (e.g. `8UP`) -> `route_name`
  - `created_at` (IST) -> `timestamp`
  - `passenger_count` -> `quantity`
  - `amount` -> `fare`
  - `vehicle_number` -> `bus_id`
  - `ticket_type_id` -> `ticket_type`
  - `is_ac` -> `is_ac`
- **UI Terminology Aligned**: Crowding badges updated to match exact hackathon specifications:
  - Low (<40%) -> **"Seats Available"**
  - Moderate (40-75%) -> **"Standing Room"**
  - High (>75%) -> **"Crowded"**
- **Canonical Test Route**: "Anand Vihar to Connaught Place, leaving at 6 PM on a weekday" established as primary showcase demo query.
