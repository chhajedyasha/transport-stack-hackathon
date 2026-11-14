# CrowdWise — Complete Website & Feature Guide

> **Official Comprehensive Guide to the CrowdWise Delhi Bus Journey Planner**  
> *Everything you need to know about every page, feature, chart, metric, and term used across the platform.*

---

## Table of Contents
1. [What is CrowdWise?](#1-what-is-crowdwise)
2. [Data Honesty & Core Philosophy](#2-data-honesty--core-philosophy)
3. [System Architecture & Data Flow](#3-system-architecture--data-flow)
4. [Complete Page-by-Page Feature Walkthrough](#4-complete-page-by-page-feature-walkthrough)
   - [4.1 Journey Planner (`/`)](#41-journey-planner-)
   - [4.2 Journey Results & Route Track (`/results`)](#42-journey-results--route-track-results)
   - [4.3 Stop-by-Stop Itinerary Timeline (`JourneyItinerary`)](#43-stop-by-stop-itinerary-timeline-journeyitinerary)
   - [4.4 Interactive Route Map (`LeafletRouteMap`)](#44-interactive-route-map-leafletroutemap)
   - [4.5 Top-3 Comparison Matrix (`CompareTable`)](#45-top-3-comparison-matrix-comparetable)
   - [4.6 Route Details & Corridor Profile (`/route/:id`)](#46-route-details--corridor-profile-routeid)
   - [4.7 Network Analytics (`/analytics`)](#47-network-analytics-analytics)
   - [4.8 Data & Method Transparency (`/about`)](#48-data--method-transparency-about)
   - [4.9 System States: Skeletons, Empty, Error, Offline & 404](#49-system-states-skeletons-empty-error-offline--404)
5. [Exhaustive Glossary of Transit & Data Terms](#5-exhaustive-glossary-of-transit--data-terms)
6. [Every Chart & Visual Representation Explained](#6-every-chart--visual-representation-explained)
7. [Accessibility & WCAG 2.2 AA Compliance](#7-accessibility--wcag-22-aa-compliance)
8. [Local Server Instructions & Key Showcase URLs](#8-local-server-instructions--key-showcase-urls)

---

## 1. What is CrowdWise?

**CrowdWise** is a crowdedness-aware public bus journey planner built specifically for commuters across the National Capital Territory (NCT) of Delhi. 

While conventional transit apps only tell you when a bus might arrive or how long a trip takes, **CrowdWise tells you how crowded that bus will likely be** along each segment of the journey, allowing commuters to make informed trade-offs between travel time and travel comfort.

### The Problem It Solves:
- In Delhi, public buses can be severely congested during morning and evening peak hours, while parallel routes or buses leaving just 15 minutes later may have plenty of space.
- Commuters—especially older adults, pregnant passengers, students, and daily office-goers—often prefer taking a bus that takes 10 minutes longer if it means avoiding an overwhelming, crushed crowd.
- Delhi's transit data has historically lacked real-time occupancy sensors. CrowdWise bridges this gap using **2.56 million official Electronic Ticketing Machine (ETM) transactions from October 2026** combined with the official **Delhi Static GTFS Schedule** to reconstruct historical passenger demand stop-by-stop.

---

## 2. Data Honesty & Core Philosophy

CrowdWise adheres to a strict standard of **data authenticity and ethical communication**:

1. **Not a Live GPS Tracking App:**
   CrowdWise displays scheduled timetable departures derived from official GTFS files. It never fakes live vehicle GPS locations, pulsing dots, or artificial "arriving in 3 min" countdowns.
2. **Demand Estimates, Not Physical Seat Counting:**
   Ticket machines record conductor fare transactions when passengers board; they do not count physical seats or automatically detect passenger alightings. Therefore, CrowdWise uses demand-based terminology by default:
   - **Not crowded** (Low passenger load)
   - **Fairly crowded** (Moderate passenger load)
   - **Very crowded** (High passenger load relative to typical fleet capacity)
   - **Not enough data** (Sparse ticket observations)
3. **Capacity Label-Style Switch:**
   Only when an API endpoint explicitly supplies verified vehicle capacity (e.g. verified low-floor 35-seat AC vs 54-seat standard bus) is seat-style wording (*"Seats available"* / *"Standing room"* / *"Crowded"*) permitted.
4. **Mandatory Transparency Line:**
   Every planning and inspection screen prominently displays:  
   `"Based on past ticket data for this time of day."`
5. **Zero Synthetic Hallucinations:**
   Every number, percentage, stop sequence, and travel time comes directly from the database and machine learning models trained on the actual hackathon datasets.

---

## 3. System Architecture & Data Flow

```
┌───────────────────────────┐      ┌─────────────────────────────┐
│    Delhi Static GTFS      │      │    October 2026 ETM Tickets │
│  (6,862 Stops, 2,574 Rts, │      │  (2.56 Million Transactions,│
│  Stop Times, Shapes)      │      │   Conductor Fare Stages)    │
└─────────────┬─────────────┘      └──────────────┬──────────────┘
              │                                   │
              ▼                                   ▼
┌────────────────────────────────────────────────────────────────┐
│                   Data Processing Pipeline                     │
│  • Normalizes stop names & matches colloquial aliases          │
│  • Reconstructs alightings via gravity / trip-length modeling  │
│  • Computes stop-to-stop segment occupancy facts (3.32M rows)  │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│          SQLite Central Transit Database (crowdwise.db)        │
│    DimStops, DimRoutes, DimTrips, StopTimes, SegmentCrowdFacts │
└─────────────────────────────┬──────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌────────────────────────────────┐
│   Flask REST API Server  │    │  Offline LightGBM Model        │
│   (Port 5000, Python)    │◄───┤  (Estimates Relative Crowding  │
│   Routing & Enveloping   │    │   Index RCI for any hour/day)  │
└─────────────┬────────────┘    └────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────────────┐
│                  Vite + React Frontend (Port 3000)             │
│  • Public Transit Design System (tokens.css, Tailwind CSS)     │
│  • Leaflet OpenStreetMap with custom SVG markers               │
│  • Recharts Diurnal Analytics & Itinerary Stop Timelines       │
│  • English and Hindi Bilingual Localization                    │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Complete Page-by-Page Feature Walkthrough

### 4.1 Journey Planner (`/`)
The homepage is a **pure utility**—it opens straight to the journey planning tool with zero marketing banners or decorative fluff.

- **From Stop (`StopCombobox`):**
  - Instant typeahead search across all 6,862 Delhi bus stops.
  - Recognizes colloquial shorthand and acronyms: typing `CP` finds *Connaught Place / Shivaji Stadium Terminal*; `ISBT` finds *Anand Vihar ISBT* and *Kashmere Gate*; `AIIMS` finds *AIIMS New Delhi*; `NDLS` finds *New Delhi Railway Station*.
  - When focused with an empty input, it instantly opens a **"Suggested Major Transit Hubs"** quick-select list featuring Delhi’s 8 highest-volume interchanges.
- **To Stop (`StopCombobox`):**
  - Destination input with identical autocomplete and alias matching.
- **Swap Button ($\updownarrow$):**
  - Instantly interchanges the origin and destination stops with a single tap (44px touch target).
- **Departure Time Selector (`DateTimeField`):**
  - Choose between `"Leave now"` (defaults to current time / 18:00 peak) or `"Leave at"` with an accessible time picker.
- **Priority / Ranking Segmented Control:**
  - **Fastest:** Strictly ranks journeys to minimize total travel time (minutes).
  - **Balanced (Default):** Weighs travel time against crowding levels, recommending journeys that save substantial comfort at minimal time expense.
  - **Least crowded:** Prioritizes routes with the lowest crowd index, ideal for passengers who need a seat.
- **Primary Search Button:**
  - High-contrast, full-width button (min 44px height). Styled to remain visible above the mobile on-screen keyboard at 360px viewport width.
- **Quick Corridor Showcase Link:**
  - A 1-click test button: `"Try corridor: Anand Vihar → Connaught Place (6:00 pm)"` that immediately pre-fills and executes the primary demonstration route.
- **Recent Searches Drawer:**
  - Automatically remembers the user’s last 5 searches in local device storage (`localStorage`).
  - Users can tap any previous search to re-run it in 1 second, or tap **"Clear recent"** to wipe their local history.

---

### 4.2 Journey Results & Route Track (`/results`)
Displays all ranked bus journey options matching the commuter’s departure and arrival stops.

- **Header Breadcrumb Bar:**
  - Shows `Origin → Destination` with scheduled departure time and the historical data disclaimer.
  - Includes a **"Back / Edit search"** button and a **"Compare top 3"** toggle button.
- **Ranked Journey Options List:**
  - Rendered using the `TransitRow` component based on `design.md`'s trip-option architecture.
  - **Route Badge (`RouteBadge`):** Bold, high-contrast navy badge showing the route number (e.g. `73UP`, `85DOWN`, `943UP`, `108AUP`).
  - **Scheduled Departure Time:** Formatted in 12-hour AM/PM (e.g. `Leaves 6:00 pm · scheduled`).
  - **Total Travel Duration:** Rendered as the largest, most prominent number in bold tabular figures (e.g. `40 min`).
  - **Corridor Distance & Stop Count:** Shows the total distance in kilometers (e.g. `13.4 km`) and total stops along the ride (e.g. `25 stops`).
  - **Dual Crowding Indicators:**
    1. Crowding at boarding stop (`At stop: Not crowded`).
    2. Crowding during the busiest part of the ride (`Busiest part: Very crowded`).
  - **"Recommended for Balanced" Pill:** Highlights why the top option was chosen, with a **"Why"** popover button detailing the exact scoring breakdown.
  - **Expandable Inline Details:**
    - Tapping the row expands an inline drawer revealing the **`TimeBreakdownBar`** (proportions of walk, wait, and ride times), **Data Confidence**, and a direct link to the **24-Hour Route Profile**.

---

### 4.3 Stop-by-Stop Itinerary Timeline (`JourneyItinerary`)
Located directly beneath the map, this Moovit-style step-by-step timeline provides complete journey details:

- **Header Strip:** Displays route badge, scheduled departure and arrival span (e.g. `6:00 pm – 6:40 pm`), total minutes, operator (`DTC`), total corridor distance, and route crowd level.
- **Boarding Stop (Origin):** Marked with a prominent teal indicator, stop name, scheduled departure time, and Stop ID.
- **Intermediate Stops (Collapsible):**
  - Displays the exact count of intermediate stops (e.g. *"23 intermediate stops"*).
  - Can be expanded or collapsed with a single tap.
  - Every intermediate stop lists its **stop sequence number** (`#2`, `#3`...), **stop name**, **cumulative distance from departure** (e.g. `+1.8 km`), and **approximate scheduled arrival time** (e.g. `6:04 pm`, `6:08 pm`).
- **Alighting Stop (Destination):** Marked with a dark navy terminal indicator, final arrival time, and cumulative distance.
- **Corridor Speed & Fare Advisory:** Displays estimated corridor operating speed (`~18 km/h`) and ticket validity (`DTC Daily / Pink Pass valid`).

---

### 4.4 Interactive Route Map (`LeafletRouteMap`)
Built with Leaflet and OpenStreetMap:

- **Dual-Cased Polyline:** The active bus path is rendered with a 6px deep navy casing overlaid with a 3.5px pine teal core line for maximum visibility over complex street grids.
- **Custom Circle Markers:**
  - Boarding stop: Large 7px teal marker with navy border.
  - Alighting stop: Large 7px navy marker with white border.
  - Intermediate stops: Clean 4px white markers with navy outlines.
  - Zero default blue Leaflet pins, preventing Vite asset-bundling breakage.
- **Interactive Stop Popups:** Tapping any stop pin displays its stop name, stop ID, sequence number, distance from origin, and scheduled arrival time.
- **Approximate Path Notice:** If raw GTFS shape geometry is absent for a secondary feeder route and the system connects stop coordinates directly, the map legend automatically surfaces an amber badge:  
  `"Approximate path between stops"`.
- **Auto-Fit Bounds:** Automatically pans and zooms to frame the exact corridor whenever a different journey option is selected.

---

### 4.5 Top-3 Comparison Matrix (`CompareTable`)
Tapping the **"Compare top 3"** button reveals a side-by-side comparison matrix of the best options:

- **Head-to-Head Attributes:**
  - Total Travel Time (Minutes)
  - Walking Time
  - Waiting Time
  - Ride Time
  - Crowding at Boarding Stop
  - Busiest Stretch of the Ride
  - Data Confidence Level
  - Transfers Count
- **Automatic Highlights:**
  - A dark navy **"Fastest"** badge is automatically attached to the option with the minimum duration.
  - A teal **"Least crowded"** badge is attached to the option with the lowest crowding score.
- **Direct Selection:** Tapping any column in the comparison table immediately selects that route and highlights its path on the map.

---

### 4.6 Route Details & Corridor Profile (`/route/:id`)
A dedicated deep-dive page for any Delhi bus route (e.g. `/route/73UP`, `/route/101UP`):

- **Route Header:** Displays RouteBadge, full agency name (`Delhi Transport Corporation`), total stops, and historical disclaimer.
- **Quick Route Switcher:** 1-click links to jump between high-volume Delhi routes (`73UP`, `85DOWN`, `108AUP`).
- **Day Type Selector (`SegmentedControl`):** Toggle between **Weekday**, **Saturday**, and **Sunday**.
- **Hour-of-Day Selector:** Dropdown to inspect conditions across all 24 hours of the day (0:00 to 23:00).
- **Vertical Stop Timeline with Crowd Colors:**
  - Displays all stops in sequence.
  - The connecting rail between consecutive stops is dynamically colored according to the estimated passenger load for the chosen hour:
    - **Green:** Not crowded
    - **Amber:** Fairly crowded
    - **Red:** Very crowded
- **24-Hour Diurnal Crowding Profile Chart:**
  - Area chart plotting estimated passenger load across all 24 hours.
  - Compares **Weekday demand (Navy line)** against **Weekend demand (Teal line)** on the same chart.
  - Surfaces a dynamic, data-computed takeaway sentence (e.g. *"Peak crowding occurs around 6:00 pm with an estimated average load of 52 passengers"*).
- **Collapsible Route Map:** Toggle button to view the full geographic route track on the Leaflet map.

---

### 4.7 Network Analytics (`/analytics`)
Provides transit planners and commuters with a system-wide overview of Delhi bus congestion:

- **4-Figure Summary Strip:**
  - **Routes covered:** 2,574 routes
  - **Tickets processed:** 2.56 Million
  - **Date range:** 01–31 Oct 2026
  - **Model status:** Active (LightGBM loaded)
- **Question 1: "When is the network busiest?"**
  - Network-wide 24-hour diurnal demand curve.
  - Illustrates the classic **twin-peak commuter phenomenon**: morning rush (8:30–9:30 am) and evening rush (5:30–7:00 pm), and shows that weekend passenger volume drops by ~35%.
- **Question 2: "Which routes are most crowded at peak?"**
  - Interactive table of Delhi’s highest-demand corridors (e.g. `717A`, `729`, `511A`).
  - Shows peak RCI, morning/evening peak hours, and proportional horizontal load bars.
  - Includes interactive column sorting by peak crowding.
- **Question 3: "How are crowd levels distributed across the network?"**
  - A horizontal proportional stacked bar revealing that **54% of operating bus hours are Not Crowded**, **32% are Fairly Crowded**, and **14% experience Very Crowded peak conditions**.

---

### 4.8 Data & Method Transparency (`/about`)
CrowdWise is completely transparent about how its predictions are made:

- **SVG Data Pipeline Architecture Diagram:**
  - Visual diagram showing the progression: GTFS Schedule $\rightarrow$ Conductor Ticketing $\rightarrow$ Alighting & Load Model $\rightarrow$ CrowdWise Journey Planner.
- **Data Tiers Table:**
  - **Tier 1 (GTFS Schedule):** Routes, stops, timetables, and shapes.
  - **Tier 2 (ETM Ticketing):** 2.56M conductor transaction logs.
  - **Tier 3 (Historical Load Model):** Stop-to-stop passenger occupancy estimates.
- **Real Model Sanity & Validation Results:**
  - **Peak Multiplier:** AM peak load reaches 2.47× midday baseline; PM peak reaches 1.84×.
  - **Physical Non-Negativity:** 0% negative passenger load violations across all 3.32M facts.
  - **Weekday vs Sunday Ratio:** Weekday demand strictly exceeds Sunday demand by 2.08×.
- **Technical Glossary & Privacy Commitment:** Explains ETM, GTFS, and RCI, and confirms that searches and locations never leave the user's browser.

---

### 4.9 System States: Skeletons, Empty, Error, Offline & 404

1. **Content-Shaped Skeletons (`Skeleton.jsx`):**
   - While routes or journey plans load, the UI displays animated pulse placeholders shaped exactly like the destination cards and map, preventing layout shift (CLS).
2. **Accessible Empty State:**
   - Displayed when no direct bus exists between two selected stops.
   - Includes a helpful **"Search wider (walk up to 800 m)"** action button that widens the search radius.
3. **Error State with Retry:**
   - If a network request fails, surfaces a clear explanation with a 1-tap **"Try again"** button.
4. **Offline Detection Banner:**
   - Automatically detects when a commuter loses mobile network connectivity (`navigator.onLine`) and displays a persistent grey banner:  
     `"You are currently offline. Timetable and prediction features may be limited."`
5. **404 Page Not Found (`NotFoundPage.jsx`):**
   - Clean, friendly page for broken URLs with a direct button back to the journey planner.
6. **Error Boundary (`ErrorBoundary.jsx`):**
   - Top-level React error catcher ensuring that unexpected runtime exceptions show a graceful recovery screen with a **"Reload page"** button rather than a blank white screen.

---

## 5. Exhaustive Glossary of Transit & Data Terms

| Term / Acronym | Full Name / Concept | What it Means in CrowdWise |
|---|---|---|
| **GTFS** | General Transit Feed Specification | The international open standard format for public transit schedules and geographic information. CrowdWise uses Delhi's static GTFS for routes, stops, trips, stop times, and shapes. |
| **ETM** | Electronic Ticketing Machine | The handheld electronic machine carried by Delhi bus conductors. Each time a commuter purchases a ticket or shows a pass, the ETM records the timestamp, boarding stop, fare, and vehicle number. |
| **RCI** | Relative Crowding Index | A normalized scale from **0 to 100** representing passenger density along a bus route segment. $\text{RCI} < 50$ is Low; $50 \le \text{RCI} < 85$ is Moderate; $\text{RCI} \ge 85$ is High. |
| **Alighting Estimation** | Passenger Departure Modeling | In Delhi, passengers buy tickets when boarding, but do not scan off when exiting. CrowdWise uses an alighting model (gravity/trip-length distribution) to mathematically estimate at which downstream stop each passenger gets off. |
| **Segment Passenger Load** | Stop-to-Stop Occupancy | The estimated total number of passengers currently on board the bus between Stop $A$ and Stop $B$. Calculated as:  $$\text{Load}_B = \text{Load}_A + \text{Boardings}_A - \text{Alightings}_A$$ |
| **Scheduled Time** | Timetable Time | Departure time specified in the GTFS schedule. Explicitly labeled *"scheduled"* to indicate it is not a live GPS vehicle location. |
| **Data Confidence** | Statistical Reliability Score | **A lot of data (High):** Route segment has dozens of daily ticket observations.  **Some data (Medium):** Moderate observations.  **Little data (Low):** Sparse observations; estimates are blended with network heuristics. |
| **Fastest Priority** | Time Optimization | Ranks journeys strictly by minimum total travel minutes. |
| **Balanced Priority** | Multi-Objective Optimization | The default CrowdWise algorithm: scores journeys using a weighted formula balancing travel duration against crowding penalty:  $$\text{Score} = \text{Duration} + (\text{RCI} \times 0.25)$$ |
| **Least Crowded** | Comfort Optimization | Prioritizes journeys that travel on the emptiest buses, even if the trip takes a few minutes longer. |
| **Colloquial Alias** | Shorthand Transit Matching | Mapping everyday commuter slang and abbreviations (e.g. `CP`, `ISBT`, `AIIMS`, `Dhaula Kuan`) to their official GTFS stop names. |
| **Corridor** | Transit Route Alignment | The continuous physical arterial road along which multiple bus routes operate (e.g. Anand Vihar to Shivaji Stadium along Vikas Marg). |

---

## 6. Every Chart & Visual Representation Explained

### A. 24-Hour Diurnal Demand Curve (Recharts Area Chart)
- **Where:** Route Details (`/route/:id`) and Network Analytics (`/analytics`).
- **What it Shows:** Passenger demand on the vertical axis (0 to 100 RCI or passenger count) across the 24 hours of the day (horizontal axis).
- **The Two Lines:**
  - **Navy Area (`#142B3B`):** Weekday travel demand showing sharp twin peaks at 9:00 am and 6:00 pm.
  - **Teal Area (`#00828A`):** Weekend travel demand showing a flatter, smoother curve with ~35% lower overall load.
- **Takeaway Caption:** A dynamic sentence below the title summarizes the peak hour and load calculated directly from the hourly dataset.

### B. Three-Segment Discrete Crowd Indicator (`CrowdIndicator.jsx`)
- **Where:** Journey result cards, comparison table, route timeline, and stop details.
- **What it Shows:** A horizontal 3-segment bar accompanied by plain-language text:
  - `[█ ░ ░] Not crowded` (Green `#15803D`, 1 segment active)
  - `[█ █ ░] Fairly crowded` (Amber `#B45309`, 2 segments active)
  - `[█ █ █] Very crowded` (Red `#B91C1C`, 3 segments active)
  - `[░ ░ ░] Not enough data` (Grey `#64748B`, 0 segments active)
- **Why Discrete Segments:** Colorblind commuters or users reading screens in direct sunlight can instantly tell the crowding level by counting the active rectangular blocks, ensuring complete non-color dependency.

### C. Time Breakdown Proportion Bar (`TimeBreakdownBar.jsx`)
- **Where:** Inside the expanded `TransitRow` card.
- **What it Shows:** A single proportional bar dividing the journey into:
  - **Grey Segment:** Walking time (minutes to/from the stop).
  - **Amber Segment (`#B45309`):** Waiting time at the stop.
  - **Teal Segment (`#00828A`):** In-vehicle ride time.
- Allows commuters to see at a glance whether a 50-minute journey is mostly sitting comfortably on a bus or standing waiting at a junction.

### D. Network Crowding Distribution Stacked Bar
- **Where:** Network Analytics page (`/analytics`).
- **What it Shows:** A horizontal segmented bar showing the proportion of all operating bus hours in Delhi:
  - **54% Green:** Off-peak hours where seats are generally available.
  - **32% Amber:** Regular hours where standing room is available.
  - **14% Red:** Severe peak-hour congestion.

### E. Stop-to-Stop Vertical Timeline Rail
- **Where:** Route Details page (`/route/:id`).
- **What it Shows:** A vertical transit line connecting all consecutive stops. The line segment between Stop $N$ and Stop $N+1$ is colored green, amber, or red based on the estimated passenger load for the currently selected hour.

---

## 7. Accessibility & WCAG 2.2 AA Compliance

CrowdWise was engineered to meet strict web accessibility standards:

1. **High Text Contrast:**
   - Primary text (`#202A32`) achieves a **14.1:1** contrast ratio on white backgrounds ($\ge 7:1$ AAA).
   - Secondary text (`#5F6B73`) achieves **5.2:1** ($\ge 4.5:1$ AA).
   - Amber crowd text is darkened to `#8A5A00` to achieve **5.1:1**, avoiding the common accessibility failure of unreadable yellow text on light backgrounds.
2. **Touch Target Size:**
   - All interactive buttons, combobox triggers, and navigation tabs have a minimum touch target height of **44 px**, ensuring effortless operation on mobile phones while walking or standing on a bumpy bus.
3. **Visible Focus Rings:**
   - Every interactive control has an explicit 2px solid teal focus ring (`:focus-visible`) with a 2px offset for keyboard and screen-reader navigation.
4. **Tabular Numerals (`tnum`):**
   - All journey durations, arrival times, and percentages use tabular numerals so numbers align perfectly without jittering as digits change.
5. **Motion Safety:**
   - All animations are restricted to `transform` and `opacity` between 120ms and 280ms.
   - Respects `prefers-reduced-motion: reduce` by instantly disabling all transitions for users sensitive to motion.
6. **Bilingual Support (English & हिन्दी):**
   - Complete 1-click language switcher (`EN` / `हिन्दी`) across all pages, terms, and button labels.

---

## 8. Local Server Instructions & Key Showcase URLs

### Starting the Servers Locally

**Backend (Flask API on Port 5000):**
```powershell
cd "c:\Users\rajsi\OneDrive\Desktop\Documents\raj\transport  hackathon\transport-stack-hackathon"
$env:FLASK_DEBUG="0"
python backend/run.py
```

**Frontend (Vite React on Port 3000):**
```powershell
cd "c:\Users\rajsi\OneDrive\Desktop\Documents\raj\transport  hackathon\transport-stack-hackathon\frontend"
npm run dev
```

---

### Key Showcase URLs to Visit

- **Homepage & Search:** [http://localhost:3000/](http://localhost:3000/)  
  *Try typing `CP` or `ISBT`, or clicking on the search input to see suggested major hubs.*
- **Journey Planner Results & Interactive Track:**  
  [http://localhost:3000/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=fastest](http://localhost:3000/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=fastest)  
  *Features the 73UP / 85DOWN corridor with full polyline track, stop pins, Moovit-style itinerary timeline, arrival times, and "Why" modal.*
- **Route 101UP 24-Hour Profile & Stop Timeline:**  
  [http://localhost:3000/route/101UP](http://localhost:3000/route/101UP)  
  *Features the weekday vs weekend dual-curve diurnal chart, hour selector, and colored stop timeline.*
- **Delhi Network Analytics:** [http://localhost:3000/analytics](http://localhost:3000/analytics)  
  *Features the system-wide diurnal twin peaks curve, sortable peak routes table, and demand breakdown.*
- **Data & Methodology Transparency:** [http://localhost:3000/about](http://localhost:3000/about)  
  *Features the SVG data pipeline flow diagram, data tiers, sanity validation metrics, and glossary.*
- **API Health Check:** [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)
