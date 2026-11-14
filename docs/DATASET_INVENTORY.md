# Dataset Inventory: Delhi Transport Stack Datasets

This document provides a factual, empirical profile of the two real datasets powering **CrowdWise**.

---

## 1. Primary Ingestion Datasets

### A. October 2026 Bus Ticketing Dataset (`October-Delhi.csv`)

| Property | Value | Notes |
| :--- | :--- | :--- |
| **File Location** | `data/raw/organizer/October-Delhi.csv` | Extracted from `October-Delhi.csv.zip` |
| **File Size** | 290,014,457 bytes (276.58 MB) | UTF-8 Comma-Separated Values |
| **Total Records** | **2,559,899 rows** | 1 header + 2,559,899 data rows |
| **Date Range Covered** | **2026-10-01 to 2026-10-31** | Complete 31 days (all of October 2026) |
| **Timezone** | `Asia/Kolkata` (`+05:30`) | Microsecond-precision timestamps |
| **Estimation Mode** | **Mode A (Exact O-D Known)** | `start_stop_name` and `end_stop_name` present on 100% of rows |

#### Column Schema & Data Quality:

| Column Name | Inferred Dtype | Null % | Distinct Values | Semantic Description |
| :--- | :--- | :--- | :--- | :--- |
| `passenger_count` | `int64` | **0.00%** | 1 – 6 | Number of passengers covered by transaction |
| `amount` | `float64` | **0.00%** | Fares (e.g. 5, 9, 13.5, 22) | Monetary fare paid in INR |
| `vehicle_number` | `string` | 52.69% | ~4,200 unique | DTC/DIMTS Bus registration (e.g. `DL1PD6826`) |
| `ticket_type_id` | `int64` | **0.00%** | 1 (Standard ticket) | Ticketing classification identifier |
| `end_stop_name` | `string` | **0.00%** | 5,761 distinct | Official or colloquial alighting destination stop |
| `route` | `string` | **0.00%** | 2,020 distinct | Route corridor + Direction (`UP` or `DOWN`) |
| `start_stop_name` | `string` | **0.00%** | 5,612 distinct | Boarding origin stop name |
| `created_at` | `string (timestamp)`| **0.00%** | 2,559,899 timestamps | Transaction issuance timestamp with `+05:30` offset |
| `is_ac` | `boolean` | **0.00%** | True (77.9%), False (22.1%)| AC Low-Floor (Electric/CNG) vs Non-AC Bus |

#### 5 Masked Sample Records:
```json
[
  {"passenger_count": 1, "amount": 22.0, "vehicle_number": "NULL", "ticket_type_id": 1, "end_stop_name": "Mahamaya Flyover West", "route": "8UP", "start_stop_name": "Ali Village", "created_at": "2026-10-28 10:19:18.780611+05:30", "is_ac": true},
  {"passenger_count": 1, "amount": 9.0, "vehicle_number": "DL***6826", "ticket_type_id": 1, "end_stop_name": "Crown Plaza", "route": "8ADOWN", "start_stop_name": "Kalindi Kunj Bdr", "created_at": "2026-10-28 10:19:29.989461+05:30", "is_ac": true},
  {"passenger_count": 1, "amount": 13.5, "vehicle_number": "DL***9760", "ticket_type_id": 1, "end_stop_name": "Clal Chowk", "route": "433UP", "start_stop_name": "Andrews Ganj", "created_at": "2026-10-28 10:19:46.297108+05:30", "is_ac": true},
  {"passenger_count": 1, "amount": 13.5, "vehicle_number": "NULL", "ticket_type_id": 1, "end_stop_name": "Ice Factory", "route": "208DOWN", "start_stop_name": "West Patel Nagar", "created_at": "2026-10-28 10:19:47.853905+05:30", "is_ac": true},
  {"passenger_count": 1, "amount": 9.0, "vehicle_number": "DL***5164", "ticket_type_id": 1, "end_stop_name": "Mallu Farm", "route": "516UP", "start_stop_name": "Chhatarpur Extension", "created_at": "2026-10-28 10:19:48.525393+05:30", "is_ac": true}
]
```

---

### B. Delhi Static GTFS Timetable Feed (`data/raw/gtfs/`)

| File | Row Count | Primary Key | Foreign Keys | Role in CrowdWise |
| :--- | :--- | :--- | :--- | :--- |
| **`routes.txt`** | 2,574 | `route_id` | `agency_id` | Connects ticket `route` string (e.g. `102AUP`) to transit agency |
| **`stops.txt`** | 6,862 | `stop_id` | - | WGS84 coordinates (`stop_lat`, `stop_lon`) for spatial indexing & maps |
| **`trips.txt`** | 80,357 | `trip_id` | `route_id`, `service_id` | Identifies scheduled bus runs and headways |
| **`stop_times.txt`** | 2,737,136 | (`trip_id`, `stop_sequence`)| `stop_id` | Defines ordered stop progression along each corridor |
| **`shapes.txt`** | 965,607 | (`shape_id`, `sequence`) | - | Renders road-following Leaflet route polylines |
| **`agency.txt`** | 2 | `agency_id` | - | DTC & DIMTS Cluster transit operators |
| **`calendar.txt`** | 1 | `service_id` | - | Standard weekly service schedule |
| **`calendar_dates.txt`**| 4 | (`service_id`, `date`) | - | Holiday schedule adjustments (e.g. Gandhi Jayanti Oct 2) |

---

## 2. Key Relationship & Mapping Findings

1. **Route Directionality Encoding:**
   - In Delhi GTFS `routes.txt`, `route_short_name` explicitly incorporates directionality (e.g. `102AUP`, `102ADOWN`, `8UP`, `433UP`).
   - Over **98.3%** of all ticket transactions match directly to a GTFS route pattern by string equality.
2. **Stop Name Resolution:**
   - Ticket records contain informal conductor abbreviations (e.g. `Clal Chowk` for `C-Lal Chowk`, `Peeragarhi` vs `Peera Garhi Metro Station`).
   - When constrained to the 30–50 candidate stops of the matched route pattern, normalized token matching achieves **77.3% exact O-D sequence matching**.
3. **Temporal Invariants & Daily Volume:**
   - Weekdays consistently record 92,000 – 102,000 tickets/day.
   - Sundays drop to 35,000 – 50,000 tickets/day (a realistic 2.4× weekday-to-Sunday ratio).
   - Morning peak (08:00–10:00) and evening peak (17:00–20:00) show sharp passenger volume spikes.

---

## 3. Data Limitations & Documented Assumptions

1. **Female Pink Pass Free Commuters:**
   - Female commuters travel free under Delhi Government policy without purchasing conventional tickets.
   - **Documented Multiplier:** Boarding volumes are scaled by $\gamma_r = 1.30$ (+30% load) based on Delhi Transport Department audit statistics.
2. **Missing Vehicle Identifiers:**
   - In 52.7% of tickets, `vehicle_number` is `NULL`.
   - **Resolution:** Passenger accumulation groups transactions by route, direction, and 30-minute departure windows, assuming standard 12-meter bus capacity ($V_{\text{cap}} = 70$) unless midi bus patterns are identified.
3. **Historical Timetable vs Live Realtime:**
   - Static GTFS timetable departure times are displayed and explicitly labeled as **"Scheduled"**.
   - Crowdedness estimates reflect historical empirical patterns across October 2026, with 3 confidence levels (*High*, *Medium*, *Low*).
