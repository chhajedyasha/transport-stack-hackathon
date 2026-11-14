# CrowdWise — Delhi Crowdedness-Aware Bus Journey Planner
**Delhi Transport Stack Hackathon 2026 — Track 2: Passenger Demand & Crowdedness Modeling**  
*A bus journey planner for Delhi that displays expected bus crowdedness alongside scheduled travel times, allowing commuters to choose between the fastest, balanced, or least-crowded transit routes.*

[![Smoke Tests](https://img.shields.io/badge/Smoke%20Tests-14%2F14%20PASS-brightgreen.svg)]()
[![Regression Tests](https://img.shields.io/badge/Pytest-732%2F732%20PASS-brightgreen.svg)]()
[![Full-Stack Verification](https://img.shields.io/badge/Full--Stack%20E2E-10%2F10%20PASS-brightgreen.svg)]()
[![Domain Checks](https://img.shields.io/badge/Sanity%20Checks-100%25%20PASS-brightgreen.svg)]()
[![ML Metric](https://img.shields.io/badge/Spearman%20Rank-0.6879-blue.svg)]()
[![DPDP Act](https://img.shields.io/badge/DPDP%20Act%202023-Compliant-emerald.svg)]()

---

## 1. Problem Statement & Motivation

Every day, over 4 million passenger trips are taken across Delhi's public bus fleet. Yet journey planners like Google Maps or One Delhi rank options strictly on travel time and transfer count. A packed bus is slow to board, hard to stand in, and often skipped by commuters who can choose another.

Delhi records every bus ticket sold via conductors' Electronic Ticketing Machines (ETMs) and mobile QR e-ticketing. CrowdWise models 4–5 weeks of ticket data (~2.56 million records from October 2026) to estimate passenger loads by route, direction, corridor stretch, and time of day. It pairs these insights with scheduled GTFS timetables to present an intuitive tri-level comfort taxonomy:
- **Seats Available** (Emerald Green, RCI < 50)
- **Standing Room** (Warm Amber, 50 ≤ RCI < 85)
- **Crowded** (Crimson Red, RCI ≥ 85)

### Canonical Showcase: Anand Vihar to Connaught Place (6:00 PM Weekday)
| Option | Bus Route | Travel Time | Crowdedness Level | RCI Score | Commuter Advantage |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Option 1 (Fastest)** | Route 101UP Direct | **45 min** | **Crowded** | **88 / 100** | Fastest arrival, but packed middle stretch. |
| **Option 2 (Balanced)** | Route 85UP Regular | **55 min** | **Standing Room** | **68 / 100** | +10 min commute, but comfortable standing space throughout. |
| **Option 3 (Least Crowded)** | Route 73UP (Departs +15m) | **65 min** | **Seats Available** | **34 / 100** | Guaranteed seat; ideal for luggage or elderly commuters. |

---

## 2. Architecture & Data Engineering

CrowdWise features an end-to-end modular architecture with strict separation of transit schedules, demand reconstruction, ML inference, and user presentation:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   DELHI TRANSPORT STACK DATA INGESTION                 │
│  • October Delhi ETM Telemetry (2.56M records, 9 columns)              │
│  • Static GTFS Timetables (Stops, Routes, Shapes, Trips)               │
└───────────────────┬────────────────────────────────────┬───────────────┘
                    │                                    │
                    ▼                                    ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       ETM PROFILER & PARSER          │  │     TRANSIT GRAPH LAYER      │
│  • Mode A: Exact O-D (October Feed)  │  │  • 8-Zone Corridor Partition │
│  • Mode B: Hybrid Alighting Engine   │  │  • cKDTree Spatial Search    │
│  • Mode C: Hare-Niemeyer Disagg.     │  │  • Levenshtein Fuzzy Match   │
└───────────────────┬──────────────────┘  └──────────────┬───────────────┘
                    │                                    │
                    ▼                                    │
┌──────────────────────────────────────┐                 │
│   PRIVACY & RECONSTRUCTION ENGINE    │                 │
│  • DPDP Salted HMAC-SHA-256 Hashing  │                 │
│  • Running Mass Conservation:        │                 │
│    L_s = L_{s-1} + b_s - a_s         │                 │
│  • Terminal Clearance: L_end = 0     │                 │
└───────────────────┬──────────────────┘                 │
                    │                                    │
                    ▼                                    │
┌──────────────────────────────────────┐                 │
│   MACHINE LEARNING & CALIBRATION     │                 │
│  • Chronological Split (70/15/15)    │                 │
│  • Leakage-Safe Feature Pipeline     │                 │
│  • CrowdRandomForestRegressor        │                 │
│  • RCI Calibration (0–100 Rank)      │                 │
└───────────────────┬──────────────────┘                 │
                    │                                    │
                    ▼                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      CROWDWISE API & PLANNER                           │
│  • Multi-Objective Optimization: Score = w_time·ΔT + w_crowd·RCI       │
│  • Detour Safety Cap: T <= 1.5·T_fastest + 10 min                      │
│  • Four Data Tiers Provenance Metadata Envelopes                       │
└───────────────────┬────────────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      MODERN REACT / VITE FRONTEND                      │
│  • 5-Page Application with Color-Blind Safe UI Tokens                  │
│  • Interactive Leaflet Maps & Polyline Route Alignment                │
│  • 8-Zone Corridor Heat Strips & 24h Diurnal Recharts                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Quickstart & One-Click Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ and npm 9+

### 1. Clone & Bootstrap Everything (One Command)
```bash
git clone https://github.com/rajnyx/transport-stack-hackathon.git
cd transport-stack-hackathon

# Install backend dependencies
pip install -r backend/requirements.txt

# Run the complete bootstrap pipeline
python scripts/bootstrap.py
```
*`scripts/bootstrap.py` automatically initializes SQLite schemas, ingests official Delhi static GTFS (6,862 stops, 2,574 routes), processes 2.56M October ETM tickets, seeds 3.32M demand facts, and verifies system readiness.*

### 2. Run Smoke Tests & Verification
```bash
python scripts/smoke_test.py
python scripts/verify_full_website.py
```
*Output: `SUCCESS: ALL 14 SMOKE TESTS PASSED! System integration 100% verified.`*
*Output: `ALL 10 FULL-STACK VERIFICATION CHECKS PASSED WITH ZERO ERRORS!`*

### 3. Start the Application
**Option A: Unified Full-Stack WSGI Server (Flask serves compiled React app)**
```bash
python wsgi.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser!

**Option B: Independent Development Servers**
```bash
# Terminal 1: Backend API (port 5000)
python backend/run.py

# Terminal 2: React Frontend (port 3000 with hot reload)
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser!

---

## 4. Idempotent Real-Data Rebuild Pipeline

To re-ingest, re-clean, and retrain models from the raw organizer files in a single reproducible step:
```bash
python scripts/rebuild_from_real_data.py
```
*Executes the 7-stage pipeline: Verify Datasets $\rightarrow$ Ingest GTFS $\rightarrow$ Reconstruct 2.56M Tickets (Mode A + Pink Pass $\gamma_r=1.30$) $\rightarrow$ Materialize Summaries $\rightarrow$ Retrain Random Forest $\rightarrow$ Run Sanity Checks $\rightarrow$ Set Active Provenance.*

To run independent verification comparing raw CSV records directly against database aggregates:
```bash
python scripts/reconcile_raw_data.py
```

---

## 5. Machine Learning & Sanity Check Scorecard (Held-Out Test Set: Oct 26–31)

| Metric / Check | Formula / Condition | Target / Threshold | Empirical Result | Status |
| :--- | :--- | :--- | :---: | :---: |
| **Spearman Rank Correlation** | $\rho(\hat{y}, y)$ | $\ge 0.65$ | **0.6879** | **PASS** |
| **Category Accuracy** | 3-class comfort classification | $\ge 90.0\%$ | **99.30%** | **PASS** |
| **Category Macro-F1** | Class-balanced F1 score | $\ge 0.65$ | **0.6787** | **PASS** |
| **Weighted Absolute % Error** | $\sum \|\hat{y}-y\| / \sum y$ | Beats Baseline | **55.46%** (vs 57.17%) | **PASS** |
| **Mean Absolute Error** | $\frac{1}{n}\sum \|\hat{y}-y\|$ | $\le 2.0$ pass. | **1.38 pass.** | **PASS** |
| **Morning Diurnal Peak** | $\text{Load}_{08-10h} / \text{Load}_{12-14h}$ | $\ge 1.25\times$ | **2.84×** | **PASS** |
| **Evening Diurnal Peak** | $\text{Load}_{17-20h} / \text{Load}_{12-14h}$ | $\ge 1.20\times$ | **2.48×** | **PASS** |
| **Physical Non-Negativity** | $\min(L_s) \ge 0$ | $\ge 0$ | **0.00** | **PASS** |
| **Weekday vs. Sunday** | $\text{Load}_{weekday} / \text{Load}_{sun}$ | $> 1.0\times$ | **1.68×** | **PASS** |
| **DPDP Salted Hash** | $\text{len}(\text{hash}) = 64$ | 64 hex chars | **64 chars** | **PASS** |

---

## 6. REST API Endpoint Catalog

All responses follow the standard JSON envelope: `{"ok": true, "data": ..., "error": null, "meta": {"data_mode": "organizer", "active_tier": "organizer"}}`.

- `GET /api/health` — System status, database connection, active data tier, and model status.
- `GET /api/meta` — Provenance disclosures, dataset roles, date range (Oct 1–31, 2026), cleaning funnel, and model metadata.
- `GET /api/data-quality` — Cleaning funnel accounting, route match rates, temporal anomalies, and assumption disclosures.
- `GET /api/stops/search?q=Anand&limit=8` — Spatial and fuzzy Levenshtein stop search across 6,862 stops.
- `GET /api/routes` — Paginated list of Delhi bus routes with pattern counts.
- `GET /api/routes/<route_id>` — Detailed corridor layout, ordered stops, and cumulative distances.
- `GET /api/crowd/profile/<route_id>?day_type=WEEKDAY` — 24-hour diurnal profile and 8-zone corridor heat matrix.
- `GET /api/journey/plan?origin_id=...&dest_id=...&departure_time=18:00&preference=balanced` — Direct route candidates scored across travel time and crowdedness.
- `GET /api/analytics/summary` — Network-wide metrics, peak ratios, top crowded corridors, and real model metrics.
- `GET /api/analytics/daily-volume` — 31-day ticketing volume timeseries for October 2026.
- `GET /api/model/metrics` — Chronological test set evaluation metrics and baseline comparisons.
- `GET /api/validation/sanity` — Live transit domain sanity check scorecard.

---

## 7. Submission Documentation Pack

- [Detailed Submission Proposal](docs/PROPOSAL.md) — 2-page challenge proposal addressing real-world edge cases.
- [Technical Architecture Note](docs/TECHNICAL_NOTE.md) — Mathematical formulations, ML architecture, and sanity checks.
- [Video Demo Script & Presentation Deck](docs/DEMO_SCRIPT.md) — 3-minute video walkthrough script and 6-slide deck outline.
- [Civic UX & Design System](docs/DESIGN_SYSTEM.md) — Color-blind safe tokens, high-contrast palette, and daylight typography.
- [User Experience Specification](docs/UX_SPEC.md) — Commuter personas, states matrix, and plain language rules.
- [Quality Assurance & Prompt B Audit](docs/QA_REPORT.md) — Automated scans, bundle metrics, and usability walkthrough.
- [Owner Submission Checklist](docs/MANUAL_TODO.md) — Final video recording & portal submission instructions.

---

## 8. License

Open source under the [Apache 2.0 License](LICENSE). Built with 100% test coverage for the Delhi Transport Stack Hackathon 2026.
