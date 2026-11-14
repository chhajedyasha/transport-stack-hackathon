# CrowdWise Technical Note: Mathematical Formulations & Architecture
**Transport Stack Hackathon 2026 — Track 2: Passenger Demand & Crowdedness Modeling**  
*Deep Technical Specification & Algorithmic Rigor*

---

## 1. Demand Reconstruction Mathematics

### 1.1 Physical Mass Conservation Recurrence
A fundamental axiom of transit demand modeling is that ticket sales represent point events, not instantaneous vehicle occupancy. To determine the passenger load $L_s$ onboard a bus operating along a stop sequence $s \in \{0, 1, \dots, N-1\}$:

$$L_s = L_{s-1} + b_s - a_s \quad \forall s \in \{1, \dots, N-1\}$$

Subject to physical boundary invariants:
1. **Initial Boundary Condition**: $L_0 = b_0$ (passenger load starts at the first stop's boardings).
2. **Terminal Boundary Clearance**: $L_{N-1} = 0$ (all passengers must alight at the final terminal stop).
3. **Physical Non-Negativity Invariant**: $L_s \ge 0 \quad \forall s$.

### 1.2 Tri-Modal Ingestion Pipeline (Modes A, B, and C)

The ingestion engine autonomously adapts to the data granularity provided:

#### Mode A: Full Origin-Destination Pairs (October Delhi Dataset)
When both `start_stop_name` and `end_stop_name` are recorded in the ETM transaction record:
$$b_s = \sum_{k} \mathbb{I}(\text{origin}_k = s) \cdot \text{passenger\_count}_k$$
$$a_s = \sum_{k} \mathbb{I}(\text{destination}_k = s) \cdot \text{passenger\_count}_k$$
Where $\mathbb{I}$ is the indicator function. Both boardings and alightings are known with certainty.

#### Mode B: Boarding-Only Inference (Hybrid Alighting Model)
When only boarding stop $i$ is recorded, alighting probabilities $P(j \mid i)$ for downstream stops $j > i$ are estimated via a convex combination of historical reverse-commute symmetry and trip length gravity decay:

$$P(j \mid i) = \alpha \cdot P_{\text{rev}}(j \mid i) + (1 - \alpha) \cdot P_{\text{grav}}(j \mid i)$$

Where:
- $\alpha = 0.70$ is the empirical mixing parameter.
- $P_{\text{rev}}(j \mid i) \propto B_{\text{return}}(j \to i)$ represents the probability that a commuter boarding at $i$ alights at $j$ based on reverse-direction commuter flow during complementary hours.
- $P_{\text{grav}}(j \mid i) \propto \exp(-\beta \cdot d(i, j))$ represents spatial exponential distance decay ($\beta \approx 0.12\text{ km}^{-1}$).
- Alightings are enforced to satisfy $\sum_{j > i} P(j \mid i) = 1.0$.

#### Mode C: Daily Aggregate Disaggregation (Hare-Niemeyer Algorithm)
When only total daily passenger boardings $D_r$ are available for route $r$, demand is distributed across scheduled trips $t \in \{1, \dots, M\}$ and stops using the integer-conserving **Hare-Niemeyer (Largest Remainder) Method**:

$$\text{Quota}_t = D_r \times \frac{w_t}{\sum_{k=1}^M w_k}$$
$$A_t = \lfloor \text{Quota}_t \rfloor$$
$$R_t = \text{Quota}_t - A_t$$

The remaining surplus tickets $S = D_r - \sum_{t=1}^M A_t$ are allocated to trips sorted by descending fractional remainders $R_t$. This guarantees that total daily passengers are strictly conserved without rounding distortion: $\sum_{t=1}^M A'_t = D_r$.

### 1.3 Unrecorded Passenger Inflation (Pink Pass Adjustment)
Delhi provides free travel to female passengers via uncounted Pink Passes. To rectify undercounting, a route-specific inflation factor $\gamma_r$ is applied to observed ticket boardings:
$$b'_s = \gamma_r \times b_s, \quad \gamma_r \in [1.20, 1.45]$$
Calibrated against Delhi Transport Department farebox revenue audit logs.

---

## 2. Spatial Graph & 8-Zone Corridor Partition

To standardize routes of varying stop lengths into comparable spatial units for machine learning, each pattern's stop sequence $s \in \{0, \dots, N-1\}$ is mapped into an 8-zone corridor representation:

$$z = \left\lfloor \frac{8 \times s}{N} \right\rfloor \in \{0, 1, 2, 3, 4, 5, 6, 7\}$$

- **Zone 0**: Origin terminal stretch (boardings dominate, alightings $\approx 0$).
- **Zones 2–5**: Mid-corridor core (peak passenger accumulation, transfer interchanges).
- **Zone 7**: Destination terminal stretch (alightings dominate, terminal evacuation).

---

## 3. Feature Pipeline & Machine Learning Architecture

### 3.1 Feature Extraction Pipeline
The leakage-safe `FeaturePipeline` generates 14 structured features per route-direction-zone-hour observation:

| Feature Category | Features | Formulation / Representation |
| :--- | :--- | :--- |
| **Cyclical Calendar** | `hour_sin`, `hour_cos` | $\sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$ |
| **Operating Day** | `is_weekend`, `day_of_week` | Binary indicators for Saturday/Sunday vs Weekday |
| **Corridor Spatial** | `zone_id`, `zone_id_norm` | Integer $z \in [0, 7]$ and normalized $z / 7.0$ |
| **Transit Supply** | `num_stops`, `total_dist_km`, `headway_minutes` | Extracted directly from static GTFS route patterns |
| **Historical Target Lookups** | `hist_mean_load`, `hist_p90_load`, `has_history` | Computed **exclusively** from training split window |

### 3.2 Chronological Split & Leakage Invariant
Data is split chronologically into 70% Train, 15% Validation, and 15% Test. The following invariant is programmatically asserted before feature extraction:
$$\max(\text{Train\_Timestamp}) < \min(\text{Val\_Timestamp}) < \min(\text{Test\_Timestamp})$$
No future information leaks into historical mean lookups or feature transforms.

### 3.3 Random Forest Regressor & Confidence Estimation
The primary model is a tuned `RandomForestRegressor` (34.4 MB) with the following hyperparameters:
- `n_estimators`: 45 decision trees
- `max_depth`: 15
- `min_samples_split`: 5
- `min_samples_leaf`: 2
- `n_jobs`: -1 (parallelized multi-core training)
- Model artifact size: 34.4 MB (compressed with joblib `compress=3` for safe remote repository distribution)

To estimate predictive confidence, individual tree predictions $\{\hat{y}_t\}_{t=1}^{100}$ are collected to calculate the 10th and 90th percentiles ($p_{10}, p_{90}$). The relative spread is defined as:
$$\text{Relative Spread} = \frac{p_{90} - p_{10}}{\max(\hat{y}, 0.1)}$$
- **High Confidence**: Relative Spread $< 0.35$ and historical observation support $\ge 10$.
- **Medium Confidence**: $0.35 \le \text{Relative Spread} < 0.75$.
- **Low Confidence**: Relative Spread $\ge 0.75$ or zero historical support.

---

## 4. Relative Crowding Index (RCI) & 3-Tier Taxonomy

Raw passenger load $L$ varies with bus size. A load of 60 passengers creates standing conditions on a 12-meter bus ($V_{cap} = 70$), but extreme crush load on a 9-meter bus ($V_{cap} = 45$).

The **Relative Crowding Index (RCI)** calibrates raw loads into a normalized 0–100 percentile rank:

$$\text{RCI}(L) = \frac{\text{Rank}(L)}{N_{\text{calib}}} \times 100 \in [0, 100]$$

Mapped directly into commuter-facing comfort tiers:
- **Seats Available (Green)**: $\text{RCI} < 50$ (Empty seating readily available).
- **Standing Room (Amber)**: $50 \le \text{RCI} < 85$ (Seats occupied; standing room comfortable).
- **Crowded (Red)**: $\text{RCI} \ge 85$ (Crush load; difficult boarding; passenger discomfort).

---

## 5. Multi-Objective Optimization & Detour Filtering

Given route candidate options $o \in \mathcal{O}$ connecting origin $O$ and destination $D$:

1. **Travel Time Penalty**:
$$\Delta T_{\text{norm}}(o) = \min\left(1.0, \max\left(0.0, \frac{T(o) - T_{\text{fastest}}}{\max(T_{\text{fastest}}, 10)}\right)\right)$$

2. **Crowdedness Penalty**:
$$\text{RCI}_{\text{norm}}(o) = \frac{\overline{\text{RCI}}(o)}{100.0}$$

3. **Composite Scoring Function**:
$$\text{Score}(o) = w_{\text{time}} \cdot \Delta T_{\text{norm}}(o) + w_{\text{crowd}} \cdot \text{RCI}_{\text{norm}}(o)$$

Where weights $(w_{\text{time}}, w_{\text{crowd}})$ are parameterized by user preference:
- **Fastest**: $(1.0, 0.0)$
- **Balanced**: $(0.5, 0.5)$
- **Least Crowded**: $(0.2, 0.8)$

4. **Detour Safeguard Constraint**:
Any candidate route violating the detour cap is strictly pruned:
$$T(o) \le 1.5 \times T_{\text{fastest}} + 10\text{ minutes}$$

---

## 6. Empirical Validation & Sanity Check Scorecard

Automated domain tests verify transport physics and model safety before deployment:

| Sanity Check | Mathematical Test Condition | Empirical Result | Status |
| :--- | :--- | :--- | :---: |
| **Diurnal Morning Peak** | $\text{Load}_{08:00-10:00} / \text{Load}_{12:00-14:00} \ge 1.25$ | **2.84×** | **PASS** |
| **Diurnal Evening Peak** | $\text{Load}_{17:00-20:00} / \text{Load}_{12:00-14:00} \ge 1.20$ | **2.48×** | **PASS** |
| **Physical Non-Negativity** | $\min(L_s) \ge 0 \quad \forall s$ | $\min = 0.00$ | **PASS** |
| **Weekday vs Sunday** | $\text{Mean Load}_{\text{Weekday}} > \text{Mean Load}_{\text{Sunday}}$ | **1.68×** | **PASS** |
| **Terminal Clearance** | $L_{\text{terminus}} = 0 \quad \forall \text{trips}$ | $0.00$ | **PASS** |
| **DPDP Salted Hash** | $\text{len}(\text{hash}) = 64 \land \text{PII} = \emptyset$ | $64$ chars, $0$ leaks | **PASS** |

### Model Benchmark Summary (Held-Out Test Set: Oct 26–31, 2026)
- **Spearman Rank Correlation**: `0.6879` (+5.0% higher than historical baseline)
- **Category Classification Accuracy**: `99.30%`
- **Category Macro-F1**: `0.6787`
- **WAPE**: `55.46%` (outperformed baseline of 57.17%)
- **MAE**: `1.38` passengers
- **Dataset Sample**: 672,416 held-out test observations / 3,322,312 total corridor facts

