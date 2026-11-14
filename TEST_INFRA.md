# TEST_INFRA.md — CrowdWise End-to-End Testing Infrastructure

## 1. Executive Summary & Testing Philosophy

CrowdWise is developed under a dual-track autonomous engineering paradigm for the **Transport Stack Hackathon 2026 (Problem 2)**. The testing track operates in parallel with milestone implementation, establishing an independent, requirement-driven, opaque-box test harness.

### Core Testing Principles
1. **Opaque-Box & Requirement-Driven**:
   Tests are derived strictly from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and authoritative Delhi transit specifications—never reverse-engineered from implementation internals. Components are evaluated through their external interfaces: schemas, mathematical invariants, API envelopes, CLI parameters, and observable commuter behavior.
2. **Four-Tier Data Provenance Enforcement**:
   Every data object, API payload, and user-facing metric must carry its provenance tier (`real_public`, `organizer`, `demo_synthetic`, `estimated`). Tests verify that synthetic data is never disguised as real telemetry, GTFS timetable times are never claimed as live GPS, and personal identifiers (PII) are salted/hashed.
3. **Progressive Testability & Zero-False-Failure Resilience**:
   During early milestones (M0–M1) before the full backend and ML services are built, tests utilize authoritative reference oracles, spec contract mocks, and schema validators. As implementation milestones complete (M1 through M5), the same test harness runs directly against the production code.
4. **Hermetic & Independent**:
   Tests do not rely on external internet access or live network daemons. Test fixtures are self-contained, reproducible, deterministic, and clean up their artifacts.

---

## 2. Four-Tier Test Architecture & Distribution

The test suite is structured into four complementary validation tiers totaling **348 test cases** (exceeding the >= 345 minimum requirement):

```
+-----------------------------------------------------------------------------------------+
|                                    CROWDWISE E2E TEST SUITE                             |
+-----------------------------------------------------------------------------------------+
| Tier 1: Feature Coverage (F01 - F30)                     | 150 Tests (5 per feature)    |
| Tier 2: Boundary & Corner Cases (F01 - F30)             | 150 Tests (5 per feature)    |
| Tier 3: Cross-Feature Interactions (Pairwise Combos)     |  32 Tests (Comprehensive)    |
| Tier 4: Real-World Delhi Transit Scenarios               |  16 Scenarios (End-to-End)   |
+----------------------------------------------------------+------------------------------+
| TOTAL TEST COUNT                                         | 348 Test Cases (PASSING)     |
+-----------------------------------------------------------------------------------------+
```

### Detailed Breakdown by Feature (F01 – F30)

| Feature ID | Feature Name | Tier 1 Tests | Tier 2 Tests | Tier 3 Pairs | Tier 4 Scenarios |
|---|---|:---:|:---:|:---:|:---:|
| **F01** | GTFS Static Ingestion | 5 | 5 | T3_01, T3_02, T3_03, T3_04, T3_31 | T4_06, T4_11 |
| **F02** | Route Directionality Resolution | 5 | 5 | T3_02 | T4_01, T4_02 |
| **F03** | Day Type Mapping | 5 | 5 | T3_03 | T4_05, T4_06 |
| **F04** | Contiguous 8-Zone Partitioning | 5 | 5 | T3_01, T3_05, T3_06, T3_07 | T4_07, T4_12 |
| **F05** | Multi-Modal Stop Search | 5 | 5 | T3_04, T3_26 | T4_01, T4_03 |
| **F06** | ETM Schema-Agnostic Ingestion | 5 | 5 | T3_08, T3_22 | T4_13, T4_14 |
| **F07** | Mode A Demand Reconstruction | 5 | 5 | T3_05, T3_09 | T4_01, T4_09 |
| **F08** | Mode B Alighting Inference | 5 | 5 | T3_06, T3_10 | T4_13 |
| **F09** | Mode C Demand Disaggregation | 5 | 5 | T3_07 | T4_10 |
| **F10** | Synthetic Ticket Simulator | 5 | 5 | T3_09, T3_10, T3_11, T3_32 | T4_01, T4_14 |
| **F11** | One-Command Data Swap Engine | 5 | 5 | T3_22, T3_23, T3_24 | T4_14 |
| **F12** | Privacy Engine & PII Salting | 5 | 5 | T3_08 | T4_13, T4_14 |
| **F13** | Chronological Split Invariant | 5 | 5 | T3_11, T3_12, T3_13 | T4_01, T4_14 |
| **F14** | Baseline Regressor | 5 | 5 | T3_12, T3_14 | T4_04, T4_15 |
| **F15** | Random Forest Regressor | 5 | 5 | T3_13, T3_14, T3_15, T3_16, T3_23, T3_32 | T4_01, T4_12 |
| **F16** | Model Evaluation Suite | 5 | 5 | T3_14, T3_29 | T4_14 |
| **F17** | Relative Crowding Index (RCI) | 5 | 5 | T3_15, T3_17, T3_28 | T4_01, T4_08 |
| **F18** | Peak/Off-Peak Sanity Harness | 5 | 5 | T3_16 | T4_01, T4_04, T4_06 |
| **F19** | Direct Route Journey Planner | 5 | 5 | T3_17, T3_18, T3_19, T3_20, T3_21 | T4_01, T4_08, T4_09 |
| **F20** | Travel & Wait Time Estimation | 5 | 5 | T3_18 | T4_01, T4_09 |
| **F21** | Multi-Objective Scoring Presets | 5 | 5 | T3_19, T3_27 | T4_08, T4_09 |
| **F22** | Max Detour Constraint Filter | 5 | 5 | T3_20 | T4_08, T4_12 |
| **F23** | Flask API & Dialect-Agnostic ORM | 5 | 5 | T3_21, T3_24, T3_25, T3_30 | All Scenarios |
| **F24** | Graceful Degradation Engine | 5 | 5 | T3_25 | T4_15, T4_16 |
| **F25** | Frontend Planner Page (/) | 5 | 5 | T3_26 | T4_01, T4_03 |
| **F26** | Frontend Results Page (/results) | 5 | 5 | T3_27 | T4_01, T4_08, T4_09 |
| **F27** | Frontend Route Details (/route/:id) | 5 | 5 | T3_28 | T4_07, T4_12 |
| **F28** | Frontend Analytics Page (/analytics) | 5 | 5 | T3_29 | T4_01, T4_06 |
| **F29** | Frontend About Page (/about) | 5 | 5 | T3_30 | T4_01, T4_14 |
| **F30** | Hackathon Documentation & Bootstrap | 5 | 5 | T3_31, T3_32 | All Scenarios |

---

## 3. Directory Layout & Organization

All test files reside under `tests/e2e/`:

```
tests/
├── __init__.py
└── e2e/
    ├── __init__.py
    ├── conftest.py                  # Shared fixtures, reference models, oracles & test clients
    ├── test_tier1_features.py       # Tier 1: 150 feature coverage tests (F01–F30)
    ├── test_tier2_boundaries.py     # Tier 2: 150 boundary and corner case tests (F01–F30)
    ├── test_tier3_combinations.py   # Tier 3: 32 pairwise cross-feature interaction tests
    └── test_tier4_scenarios.py      # Tier 4: 16 real-world Delhi transit commuter scenarios
```

---

## 4. Test Invariants & Reference Oracles

Every test verifies explicit mathematical or architectural invariants:

### 1. Zone Partition Formula (F04)
$$\text{zone\_id}(s, N) = \min\left(7, \left\lfloor \frac{s \times 8}{N} \right\rfloor\right)$$
- Guarantees contiguous, monotonic stop sequences with at most 8 zones ($0 \le \text{zone\_id} \le 7$).

### 2. Relative Crowding Index Calibration (F17)
$$\text{RCI} = \min\left(100, \max\left(0, \frac{\hat{L}}{60} \times 100\right)\right)$$
- Low Crowding: $\text{RCI} < 40$
- Moderate Crowding: $40 \le \text{RCI} \le 74$
- High Crowding: $\text{RCI} \ge 75$

### 3. Chronological Split Leakage Invariant (F13)
$$\max(D_{\text{train}}) < \min(D_{\text{val}}) < \min(D_{\text{test}})$$

### 4. Peak / Off-Peak Sanity Constraint (F18)
$$\bar{L}_{\text{weekday\_peak}} \ge 1.25 \times \bar{L}_{\text{weekday\_midday}} > \bar{L}_{\text{late\_night}}$$

### 5. Multi-Objective Scoring Preset Weights (F21)
$$\text{Score} = w_{\text{time}} \cdot \left(\frac{T_{\text{total}}}{\bar{T}}\right) + w_{\text{crowd}} \cdot \left(\frac{C_{\text{journey}}}{100}\right)$$
- Fastest: $w_{\text{time}} = 1.0, w_{\text{crowd}} = 0.0$
- Balanced: $w_{\text{time}} = 0.5, w_{\text{crowd}} = 0.5$
- Least Crowded: $w_{\text{time}} = 0.2, w_{\text{crowd}} = 0.8$

### 6. Detour Constraints (F22)
- Route Detour Ratio: $D_{\text{transit}} / D_{\text{straight}} \le 2.8$
- Travel Time Detour: $T_{\text{total}} \le 1.6 \times T_{\min}$

### 7. Standard API Envelope Schema (F23)
```json
{
  "ok": true,
  "data": { ... },
  "error": null,
  "meta": {
    "version": "1.0.0",
    "data_tier": "real_public" | "organizer" | "demo_synthetic" | "estimated",
    "data_mode": "demo" | "production",
    "timestamp": "ISO8601",
    "execution_time_ms": 42.5
  }
}
```

---

## 5. How to Run the Tests

### Full Test Suite Execution
To run all 348 E2E test cases:
```bash
python -m pytest tests/e2e/ -v
```

### Execution by Tier
```bash
# Tier 1: Feature Coverage (150 tests)
python -m pytest tests/e2e/test_tier1_features.py -v

# Tier 2: Boundary & Corner Cases (150 tests)
python -m pytest tests/e2e/test_tier2_boundaries.py -v

# Tier 3: Cross-Feature Interactions (32 tests)
python -m pytest tests/e2e/test_tier3_combinations.py -v

# Tier 4: Real-World Delhi Commute Scenarios (16 tests)
python -m pytest tests/e2e/test_tier4_scenarios.py -v
```

### Quick Summary Check
```bash
python -m pytest tests/e2e/ -q
```
