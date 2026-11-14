# CrowdWise — Design Audit (Baseline UX & UI Flaws)

**Date:** November 14, 2026  
**Auditor:** Principal Product Designer & Senior Frontend Engineer  
**Scope:** `frontend/src` (`pages/`, `components/`, `index.html`, `tailwind.config.js`)  
**Target:** Delhi public bus commuters (office workers, students, daily-wage laborers, older adults) on low-end Android devices (360px width) under bright sunlight and patchy mobile networks.

---

## 1. Inventory of Current Pages, Components, and Endpoints

### User-Facing Screens
1. **Journey Planner (`/`)** — `frontend/src/pages/PlannerPage.jsx`
2. **Journey Results (`/results`)** — `frontend/src/pages/ResultsPage.jsx`
3. **Route Details (`/route/:id`)** — `frontend/src/pages/RouteDetailsPage.jsx`
4. **Network Analytics (`/analytics`)** — `frontend/src/pages/AnalyticsPage.jsx`
5. **About / Methodology (`/about`)** — `frontend/src/pages/AboutPage.jsx`

### Shared Components
- `Navbar.jsx` (Navigation topbar)
- `Footer.jsx` (Generic marketing-style footer)
- `DemoBanner.jsx` (Data provenance bar)
- `CorridorHeatStrip.jsx` (Visual crowd representation)
- `CrowdBadge.jsx` (Crowding category pill)
- `ProvenanceBadge.jsx` (Tier badge)
- `LeafletRouteMap.jsx` (Leaflet OSM map)
- `WhyThisRouteModal.jsx` (Modal popup for scoring explanation)

### API Endpoints Consumed
- `GET /api/health`
- `GET /api/stops/search?q=...`
- `GET /api/stops/nearby?lat=...&lon=...`
- `GET /api/journey/plan?origin_id=...&dest_id=...&departure_time=...&preference=...`
- `GET /api/routes/:id`
- `GET /api/crowd/profile/:id?day_type=...`
- `GET /api/analytics/summary`
- `GET /api/analytics/daily-volume`
- `GET /api/data-quality`
- `GET /api/model/metrics`
- `GET /api/validation/sanity`

---

## 2. Identified "Generated / Vibe-Coded" Tells & UX Deficiencies

| File | Class / Pattern | Defect Description | Commuter Impact |
| :--- | :--- | :--- | :--- |
| `PlannerPage.jsx` | `h1 text-3xl font-extrabold`, `bg-gradient-to-r` | Hackathon hero banner ("Transport Stack Hackathon 2026 Showcase") and marketing copy instead of an immediate transit tool. | Commuter at a bus stop has to scroll past marketing slogans to find the search box. |
| `PlannerPage.jsx` | `rounded-2xl`, `shadow-sm`, `p-6` | Oversized, floating cards with generous white space. | Pushes the primary "Find Routes" button below the fold on 360×640 screens, especially with on-screen keyboard open. |
| `PlannerPage.jsx` | Native `<input type="time">` | Inconsistent, unstyled browser control with small touch targets. | Difficult to use one-handed on cheap Android WebViews. |
| `ResultsPage.jsx` | Nested card containers (`rounded-xl p-5 shadow-sm`) | Every journey option is an oversized card box rather than a dense, scannable transit list row. | Only 1 or 2 options visible per screen; comparison requires heavy scrolling. |
| `ResultsPage.jsx` | Trophy badges & "Top Pick" cards | Gimmicky gamification badges ("Fastest Trunk", "Top Pick") instead of plain-language transit recommendations. | Feels like a commercial booking portal rather than an authoritative public transit schedule. |
| `ResultsPage.jsx` | `WhyThisRouteModal.jsx` modal overlay | Full-screen blocking modal overlay to explain scoring. | Disruptive to flow; Back button closes entire page instead of dismissing the modal. |
| `LeafletRouteMap.jsx` | Standard Leaflet pin markers / default blue styling | Generic Leaflet styling without clear origin/destination differentiation or casing. | Blue pins obscure stop names; marker asset 404 risk under Vite bundling. |
| `RouteDetailsPage.jsx` | `text-xs text-slate-400 font-mono` | Shows internal jargon like `Zone 0`, `WAPE`, `Stop Sequence`, `Stop ID 8256`. | Incomprehensible to general public who simply need to know when the bus arrives and if it has seats. |
| `AnalyticsPage.jsx` | Unlabeled chart axes, generic cards | Dashboard-style presentation with Recharts default styling without clear commuter-answering questions. | Looks like an internal DevOps or admin dashboard rather than civic transparency. |
| `Navbar.jsx` | Generic desktop top bar | No language toggle (EN / हिन्दी); no mobile bottom navigation tab bar. | Hindi-first riders cannot switch languages; one-handed mobile navigation is clumsy. |
| `index.html` | Google Fonts CDN (`Plus Jakarta Sans`) & unpkg Leaflet | External CDN dependencies that fail on offline/slow 2G Delhi connections. | Broken typography and map rendering on patchy cellular data. |
| Global CSS | Variable-width numbers (`font-sans`) | Numeric times (e.g. `18:04`, `42 min`) jump and misalign across rows. | Hard to compare journey durations at a glance. |
| All files | Hardcoded English strings | Zero localization support; no Hindi text. | Inaccessible to millions of non-English speaking Delhi DTC riders. |

---

## 3. Preserved API & Honesty Contracts
The redesign strictly preserves:
1. **API Envelope & Provenance:** The factual data provenance line (`meta.provenance`, `data_tier`) stays visible.
2. **Scheduled vs. Live:** Timetable-derived departure times remain explicitly labeled **"scheduled"**.
3. **Statistical Honesty:** Predictions are labeled as estimates based on historical October 2026 ETM patterns.
4. **Low Confidence / Insufficient Data:** Displays clear "Not enough data" states whenever data is sparse.
5. **Exact API Crowd Levels:** Strictly mapped to Low, Moderate, High, Insufficient data.

---

## 4. Baseline Screenshots Log
Baseline screenshots captured via headless Chromium across 3 viewports (360×640, 768×1024, 1440×900) are cataloged in `docs/design/before/`.
