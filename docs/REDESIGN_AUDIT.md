# CrowdWise — Frontend Redesign Audit

**Date:** November 14, 2026  
**Auditor:** Principal Product Designer & Senior Frontend Engineer  
**Scope:** Full review of existing CrowdWise frontend (`frontend/src/`) against `design.md` (Transit visual system) and strict Transport Stack data honesty requirements.

---

## 1. Inventory of Existing Frontend Assets

### Pages & Routes
- **`PlannerPage.jsx` (`/`)**: Core departure/destination form with swap button, departure time selector, 3-way priority control, recent searches, and corridor showcase quick-action.
- **`ResultsPage.jsx` (`/results`)**: Split-pane layout (desktop fixed sidebar + Leaflet map; mobile map + BottomSheet) displaying ranked itinerary options, route polyline track, stop-by-stop itinerary timeline, and comparison table.
- **`RouteDetailsPage.jsx` (`/route/:id`)**: Vertical stop timeline with hourly crowdedness bars, day-type selector (Weekday/Saturday/Sunday), and 24-hour diurnal profile chart.
- **`AnalyticsPage.jsx` (`/analytics`)**: Network-wide diurnal demand curve, peak-hour crowded route rankings, and demand concentration distributions.
- **`AboutPage.jsx` (`/about`)**: Factual methodology disclosure, SVG data pipeline architecture diagram, and automated model validation status.
- **`NotFoundPage.jsx` (`*`)**: 404 fallback with clear return navigation.

### Component Primitives
1. `Button.jsx`: Touch-friendly action button with primary, secondary, navy, and ghost variants.
2. `TextField.jsx`: High-contrast form text input with clear focus ring.
3. `StopCombobox.jsx`: Accessible transit autocomplete with quick-select hub suggestions, recent searches, and geolocation.
4. `DateTimeField.jsx`: "Leave now" vs "Leave at" time selector.
5. `SegmentedControl.jsx`: Accessible 3-way radio group for priority ranking (Fastest, Balanced, Least crowded).
6. `RouteBadge.jsx`: Compact high-contrast bus badge (pill/rounded rectangle).
7. `CrowdStrip.jsx` / `CrowdBadge.jsx`: Three-segment horizontal crowd indicator with plain-language labels.
8. `TimeBreakdownBar.jsx`: Proportional walk / wait / ride time visual bar.
9. `TransitRow.jsx`: Primary trip option card with duration, departure time, and crowd indicators.
10. `JourneyItinerary.jsx`: Detailed stop-by-stop timeline with arrival times and cumulative distance.
11. `LeafletRouteMap.jsx`: Leaflet OpenStreetMap view with custom circle markers and route polyline casing.
12. `BottomSheet.jsx`: Mobile snap-point bottom drawer (`peek`, `half`, `full`).
13. `CompareTable.jsx`: Side-by-side comparison of top 3 options.
14. `Skeleton.jsx`: Content-shaped skeleton loaders.
15. `EmptyState.jsx` / `ErrorState.jsx`: Accessible zero-data and network recovery states.
16. `WhyThisRouteModal.jsx`: Scoring explanation modal with score breakdown.
17. `DemoBanner.jsx`: Data authenticity and provenance indicator bar.
18. `Navbar.jsx`: 56px sticky top navigation bar with language toggle (EN/HI).
19. `Footer.jsx`: Attribution and data provenance footer.

### State & API Calls
- `api.js`: Clean REST API client consuming backend endpoints (`/api/health`, `/api/stops/search`, `/api/stops/suggested`, `/api/journey/plan`, `/api/routes/:id`, `/api/crowd/profile/:id`, `/api/analytics/summary`, `/api/model/metrics`).
- State management: Local React state (`useState`, `useEffect`, `useMemo`) with persistent `localStorage` for user preferences and recent searches. Shareable query parameters in URLs (`origin_id`, `dest_id`, `departure_time`, `preference`).

---

## 2. Generated-Looking Tells & Visual Flaws Identified

During our thorough audit of the existing codebase and baseline screenshots (`docs/design/before/`), the following AI-generated tells and inconsistencies were identified:

1. **Inconsistent Seat vs Demand Terminology in `CrowdBadge.jsx`**:
   - *Flaw:* `CrowdBadge.jsx` hardcoded seat-oriented labels (`Seats Available`, `Standing Room`) even though the ticketing dataset only measures conductor transactions, not physical seating availability.
   - *Fix:* Enforce data honesty rule: default to demand-based wording (`Not crowded`, `Fairly crowded`, `Very crowded`) with the mandatory disclaimer: *"Based on past ticket data for this time of day."* Allow seat-style wording only if the API explicitly supplies verified vehicle capacity.

2. **Residual Marketing Card Aesthetics & Nested Containers**:
   - *Flaw:* `TransitRow.jsx` and `JourneyItinerary.jsx` occasionally used nested cards with stacked borders and default Tailwind shadows (`shadow-card`, `border-transit-border`), creating visual clutter.
   - *Fix:* Adopt `design.md`'s container rule: single clean card layer with subtle neutral border (`#DDE2E3`), zero drop shadow on content cards, and crisp hierarchy.

3. **Color Contrast & Semantic Separation**:
   - *Flaw:* The brand primary teal (`#147D78`) was sometimes visually adjacent to green crowd indicators (`#1B7F52`), causing confusion between brand action colors and semantic "Low Crowdedness".
   - *Fix:* Separate the brand primary into an authoritative Deep Navy (`#142B3B` / `#182A3A`) for structure/chrome and Deep Pine Teal (`#0F6B72` / `#00828A`) for primary actions, leaving bright emerald green (`#15803D`) exclusively for "Not crowded".

4. **Default Recharts & Leaflet Styling Tells**:
   - *Flaw:* Charts used standard generic strokes and default tooltip containers; Leaflet popups had generic styling.
   - *Fix:* Restyle charts with dedicated design tokens (`#142B3B` navy lines, `#00828A` fills, subtle `#E2E6E8` grids), tabular numerals, and custom HTML/SVG map markers that never fail to bundle under Vite.

5. **Missing Dedicated SVG Wordmark & App Mark**:
   - *Flaw:* The header rendered plain text "CrowdWise" without a cohesive brand mark.
   - *Fix:* Design a custom, self-made CrowdWise SVG wordmark and mark representing scheduled transit and passenger volume wisdom.

---

## 3. Redesign Plan by Page

- **Planner (`/`)**:
  - Remove any marketing fluff. The first viewport IS the tool.
  - Generous input spacing per `design.md` rhythm.
  - Accessible Swap button with 44px touch target.
  - Recent searches drawer with 1-click recall and clear control.
  - Ensure search button remains visible above mobile keyboard at 360x640.

- **Results (`/results`)**:
  - Desktop: Fixed 420px left panel with trip options + full-height interactive Leaflet map.
  - Mobile: Route summary header, 35% height Leaflet map, BottomSheet with snap points (`peek` 140px, `half` 52vh, `full` 92vh).
  - Adopt `design.md` trip-option layout: bold RouteBadge, largest duration number in tabular numerals, walk/wait/ride `TimeBreakdownBar`, 3-segment `CrowdStrip`, and "Why" popover.
  - Integrated `JourneyItinerary` timeline below the map.

- **Route Details (`/route/:id`)**:
  - Split view: left vertical stop timeline with segment crowd indicators; right 24-hour diurnal profile chart and route map.
  - Hour selector (0–23) and Day Type switcher (Weekday/Saturday/Sunday).
  - One-sentence dynamic takeaway computed directly from hourly data.

- **Analytics (`/analytics`)**:
  - Question-based headings (`When is the network busiest?`, `Which routes are most crowded at peak?`).
  - Axis labels with explicit units, light gridlines, custom tooltips, and calculated takeaway sentences.

- **Data & Method (`/about`)**:
  - Pure public utility style: crisp typography, SVG data architecture pipeline, model calibration table, and privacy commitment.
