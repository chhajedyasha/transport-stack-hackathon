# TODO.md — CrowdWise Phase Tracker

## Phase 0: Setup & Scaffolding
- [x] Save master prompt verbatim to `docs/MASTER_SPEC.md`
- [x] Create `AGENTS.md` (autonomy & integrity contract)
- [x] Create architecture spec `docs/ARCH.md`
- [x] Create design system & UI tokens `docs/DESIGN.md`
- [x] Create manual owner checklist `docs/MANUAL_TODO.md`
- [ ] Create initial configuration files (`config/crowd.yaml`, `config/planner.yaml`, `config/schema_mapping.yaml`)
- [ ] Create `.env.example`, `.gitignore`, `docker-compose.yml`

## Phase 1: Static Transit Layer (GTFS)
- [ ] Create `scripts/ingest_gtfs.py` (download Delhi open GTFS or build fallback fixture)
- [ ] Build derived tables (stops, routes, route_patterns, route_stops, trip_starts, supply)
- [ ] Implement 8-zone partition formula: `zone_id = min(7, floor(8 * seq / N))`
- [ ] Implement stop text search and nearest-by-coordinate (haversine / cKDTree)
- [ ] Write `docs/GTFS_REPORT.md`
- [ ] Unit tests for static transit layer

## Phase 2: Data Pipeline & Demand Reconstruction
- [ ] Implement synthetic ticket generator `scripts/generate_demo_data.py` (35 days, radial asymmetry, ground truth)
- [ ] Build data profiling tool `backend/ml/profile_data.py`
- [ ] Implement schema mapping & cleaning funnel (timestamp parsing, deduplication, PII hashing)
- [ ] Implement Load Reconstruction: Mode A (exact O-D), Mode B (inferred alightings), Mode C (route demand)
- [ ] Ground-truth validation script & tests
- [ ] Implement data swap script `scripts/swap_data.py`

## Phase 3: Machine Learning & Crowdedness Estimation
- [ ] Construct modeling dataset at (route-direction, zone, date, hour) grain
- [ ] Implement chronological train/validation/test split with leakage assertion
- [ ] Implement baseline models (B1: historical median, B2: network median)
- [ ] Train RandomForestRegressor with tree-variance confidence intervals
- [ ] Build evaluation suite (MAE, RMSE, WAPE, Spearman rank correlation)
- [ ] Build peak vs off-peak sanity check harness (`backend/ml/sanity_checks.py`)
- [ ] Generate model card and precompute prediction artifacts
- [ ] Create `scripts/retrain.py`

## Phase 4: Backend API & Journey Planner
- [ ] Define SQLAlchemy models (dual-dialect SQLite / PostgreSQL)
- [ ] Implement Flask application factory with CORS and standard envelope
- [ ] Implement endpoints: `/api/health`, `/api/stops`, `/api/routes`, `/api/crowd`, `/api/journey/plan`, `/api/analytics`
- [ ] Implement journey planner candidate generation (direct routes, 500m radius)
- [ ] Implement transparent multi-objective scoring (Fastest, Balanced, Least Crowded)
- [ ] Implement graceful degradation on empty DB or missing model file
- [ ] Document all endpoints in `docs/API.md`
- [ ] Write API contract tests

## Phase 5: Frontend Application
- [ ] Scaffold React + Vite + Tailwind CSS project
- [ ] Implement CrowdWise brand identity & SVG logo
- [ ] Implement persistent demo banner & provenance chips
- [ ] Build Page 1: Planner (`/`) with autocomplete & map preview
- [ ] Build Page 2: Results (`/results`) with option cards & comparison matrix
- [ ] Build Page 3: Route Details (`/route/:routeId`) with Leaflet polyline & hourly chart
- [ ] Build Page 4: Analytics (`/analytics`) with peak-hour charts & busiest routes
- [ ] Build Page 5: About (`/about`) with methodology, sanity scorecard & tier disclosures
- [ ] Verify responsive layout at 390px mobile and 1280px desktop

## Phase 6: Integration & Verification Loop
- [ ] Verify one-command setup: `python scripts/bootstrap.py --demo`
- [ ] Run full pytest suite
- [ ] Run `scripts/smoke_test.py` across all endpoints
- [ ] Run `scripts/doctor.py` environment check
- [ ] Verify empty database behavior

## Phase 7: Hackathon Documentation & Submission Pack
- [ ] Complete `docs/PROPOSAL.md` (2-page problem & solution proposal)
- [ ] Complete `docs/TECHNICAL_NOTE.md` (3-page methodology & validation note)
- [ ] Complete `docs/DEMO_SCRIPT.md` (3-minute presentation script & slide deck)
- [ ] Update `README.md` with complete setup instructions
- [ ] Prepare cloud deployment configurations

