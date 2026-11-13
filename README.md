# CrowdWise — Delhi Bus Crowdedness-Aware Journey Planner

> **Delhi Transport Stack Hackathon 2026 — Problem 2**  
> A bus journey planner for Delhi that displays expected bus crowdedness alongside scheduled travel times, allowing commuters to choose between the fastest, balanced, or least-crowded transit routes.

---

## Overview
CrowdWise models passenger loads across Delhi's vast bus network by marrying open static GTFS timetables with electronic ticketing machine (ETM) telemetry.

### Key Capabilities
- **Direct Route Planner**: Multi-objective journey optimization with 3 commuting presets:
  - **Fastest** (minimizes total transit time)
  - **Balanced** (balanced trade-off between wait/travel time and crowding)
  - **Least Crowded** (prioritizes low crowding, capped at a maximum 1.5x detour)
- **8-Zone Corridor Partitioning**: Divides bus routes into contiguous spatial segments to track where crowding builds and dissipates.
- **Four-Tier Data Provenance**:
  - `real_public`: Delhi Buses static GTFS (routes, stops, timetables).
  - `organizer`: Real conductor ETM ticketing logs from hackathon organizers.
  - `demo_synthetic`: Realistic synthetic passenger flow simulator with ground truth.
  - `estimated`: Reconstructed passenger loads and machine-learning predictions.
- **Leakage-Safe Machine Learning**: Chronologically split RandomForestRegressor forecasting load per scheduled trip with tree-variance confidence intervals.

---

## Project Structure
```
transport-stack-hackathon/
├── backend/          # Flask REST API, SQLAlchemy ORM, and ML models
├── frontend/         # React 18 + Vite + Tailwind CSS responsive web app
├── scripts/          # Automation (bootstrap.py, generate_demo_data.py, swap_data.py)
├── config/           # Crowding thresholds, planner weights, schema mappings
├── docs/             # Master spec, architecture, design system, proposal, tech note
├── data/             # Transit GTFS feeds & processed parquet tables (git-ignored)
└── tests/            # Automated pytest suite & contract tests
```

---

## Documentation
- [System Architecture](docs/ARCH.md)
- [Design System & UI Tokens](docs/DESIGN.md)
- [Owner Action Checklist](docs/MANUAL_TODO.md)
- [Master Specification](docs/MASTER_SPEC.md)
- [Autonomy & Integrity Contract](AGENTS.md)

