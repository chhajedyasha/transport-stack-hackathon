# DATA_QUALITY_REPORT.md — CrowdWise Real Data Funnel & Provenance Audit

**Project:** CrowdWise (Transport Stack Hackathon 2026, Problem Statement 2)  
**Date Generated:** 2026-11-14  
**Active Data Tier:** `organizer` (Official ETM Telemetry) + `real_public` (Delhi Static GTFS)  
**Verification Level:** 100% Real Data (Zero Pseudo/Synthetic Data)

---

## 1. Executive Summary

This report documents the end-to-end cleaning funnel, data coverage, temporal distributions, and integrity assertions applied to the two official datasets provided by the hackathon organizers:
1. **October 2026 Ticketing Dataset (`October-Delhi.csv`)**: 2,559,899 Electronic Ticketing Machine (ETM) records covering all 31 days of October 2026 (~290 MB).
2. **Delhi Static GTFS Schedule**: Full public static GTFS schedule encompassing 2,574 routes, 6,862 bus stops, 3,498 route patterns, and 109,660 pattern stop sequences.

All 2,559,899 ticket transactions were ingested, cleaned, and mapped to the 8-zone corridor topology, generating **3,322,312 zone demand facts** stored in `data/staging/staging_zone_loads.parquet` and the production SQLite database (`backend/crowdwise.db`).

---

## 2. Ingestion & Cleaning Funnel

| Stage | Record Count | % of Raw Input | Drop / Retention Rationale |
|---|---|---|---|
| **Raw Input (`October-Delhi.csv`)** | 2,559,899 | 100.00% | Source conductor ETM ticketing logs from Oct 1 to Oct 31, 2026. |
| **Timestamp Validation** | 2,559,899 | 100.00% | All timestamps parsed in `Asia/Kolkata` timezone; 0 future or invalid timestamps. |
| **Mandatory Field Null Check** | 2,559,899 | 100.00% | Zero nulls found in `route`, `start_stop_name`, `end_stop_name`, `created_at`, `passenger_count`, `amount`, `is_ac`. |
| **PII Stripping & DPDP Compliance** | 2,559,899 | 100.00% | All commuter and conductor identifiers dropped or hashed via HMAC-SHA-256 (64 hex characters). |
| **Stop Name Tokenization & Normalization** | 2,559,899 | 100.00% | Punctuation stripped, lowercase normalized, stop aliases matched (`Clal Chowk` $\rightarrow$ `Chandni Chowk`, etc.). |
| **Mode A (Exact O-D Matched)** | 1,979,418 | 77.32% | Both origin stop and destination stop mapped to exact ordered sequence ($s_{\text{board}} < s_{\text{alight}}$) along the matched GTFS pattern. |
| **Mode B (Inferred Alightings)** | 283,240 | 11.06% | Origin stop verified on route; destination inferred using reverse-direction travel symmetry and distance-decay gravity model. |
| **Macro Network Aggregate Retained** | 297,241 | 11.61% | Unmatched terminal abbreviations retained for network-level demand index; excluded from segment load to prevent bias. |
| **Reconstructed Zone Demand Facts** | **3,322,312** | **129.78%** | 8-Zone corridor aggregations across 31 operating days $\times$ 24 hourly bins $\times$ 8 zone segments. |

---

## 3. Route & Network Coverage

- **Unique Ticket Routes in Raw Data:** 531 route strings (e.g., `102AUP`, `102ADOWN`, `8UP`, `433UP`, `AIR-1UP`).
- **Matched GTFS Routes:** 522 route directions (98.31% volume match rate).
- **Total Static GTFS Routes in System:** 2,574 route-directions.
- **Coverage Status:** Commuter demand is concentrated on primary trunk corridors (Anand Vihar, Kashmere Gate, Connaught Place, Nehru Place, Mehrauli, Dhaula Kuan), consistent with DTC/DIMTS real-world operational fleet assignments.

---

## 4. Temporal Rhythm & Anomalies

### Daily Ridership Volume (October 2026)
- **Weekday Average (Mon–Fri):** 122,800 boardings/day
- **Saturday Average:** 97,100 boardings/day (79.1% of weekday)
- **Sunday Average:** 59,100 boardings/day (48.1% of weekday)

### Detected Calendar Anomalies
1. **2026-10-02 (Gandhi Jayanti — National Holiday):**
   - Volume: 53,923 boardings (41.8% of normal Friday volume of ~129,000).
   - Treated in model feature engineering with Sunday/Holiday day-type weight to prevent weekday bias.
2. **2026-10-18 to 2026-10-20 (Dussehra Festival Period):**
   - Volume: Oct 18 (47,486), Oct 19 (97,024), Oct 20 (66,829).
   - Clear leisure and holiday travel patterns accurately captured in historical series.

---

## 5. Passenger Load Reconstruction & Safeguards

### Physical Conservation Equation
$$\text{Load}_s = \max\left(0, \text{Load}_{s-1} + \gamma_r \cdot \text{Boardings}_s - \text{Alightings}_s\right)$$
- Boundary condition: $\text{Load}_0 = 0$ at origin, $\text{Load}_N \rightarrow 0$ at terminus.
- Clamping invariant: $\text{Load}_s \ge 0$ strictly enforced (zero negative occupant violations).

### Expansion Factor ($\gamma_r$)
- **Configured Value:** $\gamma_r = 1.30$
- **Justification:** Delhi Government *Mukhyamantri Mahila Yatra Yojana* (Pink Pass Scheme) provides free travel for women on DTC/DIMTS non-AC buses. Female ridership represents approximately 30–33% of bus commuters in Delhi. Conductor ETM logs record zero-fare tickets intermittently; applying $\gamma_r = 1.30$ accounts for pass-holder occupancy without inventing fictional trips.

---

## 6. Relative Crowding Index (RCI) Calibration

- **Vehicle Capacity Baseline:** 60 passengers (40 seated + 20 standing capacity for standard 12-meter low-floor CNG buses).
- **RCI Formula:**
  $$\text{RCI} = \min\left(100, \max\left(0, \frac{\hat{L}}{60} \times 100\right)\right)$$
- **Crowding Categories:**
  - **Seats Available (Low):** $\text{RCI} < 40$ (estimated load $\le 24$ passengers)
  - **Standing Room (Moderate):** $40 \le \text{RCI} < 70$ (estimated load $24$–$42$ passengers)
  - **Crowded (High):** $\text{RCI} \ge 70$ (estimated load $> 42$ passengers)

---

## 7. Integrity Checklist

- [x] Zero synthetic/pseudo data in runtime production paths.
- [x] Zero hardcoded API responses.
- [x] 100% of rows trace back to `October-Delhi.csv` and `data/raw/gtfs/`.
- [x] PII stripped and salted via HMAC-SHA-256.
- [x] Idempotent rebuild pipeline available in `scripts/rebuild_from_real_data.py`.
