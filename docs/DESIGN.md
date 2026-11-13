# DESIGN.md — CrowdWise Design System & UI/UX Specification

## 1. Design Philosophy
CrowdWise is designed to feel like an authoritative, high-utility public transit tool for millions of Delhi daily commuters. It avoids student-dashboard aesthetics, focusing on clarity, speed, color-blind accessibility, and transparent data provenance.

## 2. Design Tokens
- **Background Canvas**: `#F7FAFC` (light neutral gray)
- **Card & Surface**: `#FFFFFF` (clean white)
- **Primary Text**: `#0B1F3A` (deep navy)
- **Secondary Text**: `#4A5568` (slate neutral)
- **Accent Brand**: `#0FA3A3` (transit teal)
- **Border / Divider**: `#E2E8F0`

### Crowdedness Color Palette (Color-Blind Safe)
Crowding levels are **never indicated by color alone** — always combined with an icon and explicit text label:
- **Low Crowdedness**: `#22A06B` (Emerald Green) + `SeatAvailable` Icon + "Low" label (RCI < 50)
- **Moderate Crowdedness**: `#F5A623` (Warm Amber) + `StandingRoom` Icon + "Moderate" label (RCI 50–85)
- **High Crowdedness**: `#E5484D` (Crimson Red) + `CrushedFull` Icon + "High" label (RCI > 85)

## 3. Provenance & Trust UI Tokens
- **Demo Mode Banner**: Persistent top bar in high-contrast navy `#0B1F3A` with yellow badge `#F5A623`:
  `DEMO MODE: Ticket data is simulated. Timetable is scheduled static GTFS.`
- **Data Tier Chips**:
  - `[Timetable: GTFS]` (Slate pill)
  - `[Simulated Tickets]` (Amber pill, in demo mode)
  - `[Organizer ETM]` (Blue pill, when real data loaded)
  - `[Estimated Flow]` (Purple pill, for inferred alightings / model predictions)

## 4. Five Core Pages & Layouts

### Page 1: Journey Planner (`/`)
- Clean search container with responsive origin and destination stop autocomplete.
- Quick switch button (swap origin and destination).
- Departure time selector (defaulting to current local time).
- Preference Toggle segmented control:
  - `Fastest` (Minimize travel time)
  - `Balanced` (Default 50/50 trade-off)
  - `Least Crowded` (Prioritize low crowding, max 1.5x detour cap)
- Interactive Map preview for clicking stops.
- 3-step "How CrowdWise Works" informational section.

### Page 2: Journey Results (`/results?origin=...&dest=...&time=...&pref=...`)
- Shareable URL with query params.
- Filter and sorting bar (instantly re-sort without server refetch).
- Route Option Cards:
  - Total duration breakdown (walk time, wait time, in-bus travel time).
  - Prominent Crowdedness Badge (RCI value, Low/Moderate/High badge, confidence level).
  - Recommended pick highlighted with "Why this route?" popover explaining the exact score calculation.
  - Side-by-side comparison matrix for the top 3 options.
  - Route preview map showing the selected polyline.

### Page 3: Route Corridor Details (`/route/:routeId`)
- Full interactive Leaflet map displaying the actual GTFS shape polyline and ordered stops.
- Direction toggle (e.g. Anand Vihar to ISBT Kashmiri Gate vs Reverse).
- 8-Zone Corridor Heat Strip: visual progression of crowding from first stop to terminal.
- 24-Hour Crowding Profile Chart (Recharts line/bar chart comparing Weekday vs Saturday vs Sunday).
- Scheduled run time and scheduled trips per hour (frequency/headway).

### Page 4: System Analytics (`/analytics`)
- High-level system statistics: Total routes mapped, total stops, peak crowding window.
- Network Crowding by Hour chart (AM Peak 8-10 AM, PM Peak 5-8 PM, Midday, Night).
- Top 5 Most Crowded Corridors table.
- Multi-Route Comparison tool (select 2-3 bus routes to compare their crowding curves).

### Page 5: About & Methodology (`/about`)
- Full disclosure of the four data tiers.
- Honest methodology explanation (Modes A, B, and C).
- Clear statement on why ticket counts != passengers on board.
- Transparent formula for Relative Crowding Index (RCI) and scoring weights.
- Live Sanity-Check scorecard displaying automated PASS / WARN validation results.
- Data Privacy & DPDP Act compliance declaration.

## 5. API Response Envelope
Every endpoint returns a consistent JSON envelope:
```json
{
  "ok": true,
  "data": { ... },
  "error": null,
  "meta": {
    "data_mode": "demo" | "organizer",
    "provenance": {
      "timetable": "real_public",
      "tickets": "demo_synthetic",
      "crowd": "estimated"
    },
    "model_version": "1.0.0",
    "generated_at": "2026-11-13T19:50:00+05:30"
  }
}
```
In case of error:
```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "ROUTE_NOT_FOUND",
    "message": "The specified route ID does not exist in the GTFS timetable.",
    "details": null
  },
  "meta": { ... }
}
```

