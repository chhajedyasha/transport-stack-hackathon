# CrowdWise — UX Specification & Product Architecture

**Status:** Approved Specification  
**Version:** 3.0 (Public Transit Edition)  
**Target:** Delhi NCT Daily Commuters & General Public  
**Reading Level:** Grade 8 (Plain Language, Zero Transit Jargon)

---

## 1. Commuter Personas

### Persona 1: Ramesh Kumar (Daily Construction Worker, 44, Jahangirpuri)
Ramesh commutes 6 days a week from Jahangirpuri to construction sites near Lajpat Nagar and AIIMS. He uses a 4-year-old budget Android phone (360×640 px screen) with cracked glass and erratic 4G mobile data. He reads Devanagari Hindi far more comfortably than English and uses public transit with one hand while holding a metal tiffin or hanging onto a bus ceiling bar.
* **Core Need:** Wants to know in 3 seconds: *Which bus? When does it leave? Will I be crushed inside or get a place to stand?*
* **Design Constraint:** Must work flawlessly in bright outdoor sunlight (7:1 contrast on numbers and badges), with huge 44px+ touch targets, simple Hindi words, and zero complex menus.

### Persona 2: Priya Sharma (DU South Campus College Student, 19, Rohini)
Priya commutes from Rohini Sector 22 to South Campus for morning lectures. Her bus corridor is notoriously crowded during morning rush hour (8:00 AM – 9:30 AM). She often leaves 20 minutes earlier if a less-crowded bus allows her to read her notes in a seat.
* **Core Need:** Wants to compare departure options: *Is taking a bus 10 minutes later worth the 50% extra standing crush?*
* **Design Constraint:** Needs side-by-side trade-off clarity (Travel Time vs. Comfort) without confusing statistics or marketing fluff.

### Persona 3: Suresh Chand (Retired Government Clerk, 67, Mayur Vihar)
Suresh travels bi-weekly from Mayur Vihar to Ram Manohar Lohia (RML) Hospital and Connaught Place for medical appointments and pensions. He has mild macular degeneration, requires large readable text (16px+ body, 200% browser zoom support), and is easily intimidated by complex tech apps with modal popups or gesture carousels.
* **Core Need:** Obvious, step-by-step navigation without surprises: enter origin stop, enter hospital stop, see clear timetable departures.
* **Design Constraint:** Zero gestures required; full keyboard and screen reader accessibility; high contrast; no modal takeovers.

---

## 2. Top Tasks & Commuter Task Flows

```
[1. WHICH BUS?]  ──────►  [2. WHEN DOES IT LEAVE?]  ──────►  [3. HOW CROWDED?]
   Stop Search               Scheduled Departure               Plain-Language Strip
   (Autocomplete)            (12-hr am/pm)                     (Not / Fairly / Very)
```

### Flow 1: Immediate Bus Catching ("Leave Now")
1. Commuter opens `crowdwise.delhi.gov` (or tap app bookmark).
2. Input "From": Types 3 letters (e.g. "Ana") $\rightarrow$ instant match "Anand Vihar ISBT Terminal".
3. Input "To": Types "Shi" $\rightarrow$ instant match "Shivaji Stadium Terminal (Connaught Place)".
4. Departure defaults to **"Leave now"**. Preference defaults to **"Balanced"**.
5. Commuter taps primary button **"Search"** (visible even with on-screen keyboard open).
6. Result screen shows 3–4 dense rows. Commuter immediately sees:
   - Route `73UP` · Leaves 18:05 (scheduled) · 40 min · **Very crowded**
   - Route `85DOWN` · Leaves 18:12 (scheduled) · 50 min · **Fairly crowded**
   - Route `108AUP` · Leaves 18:15 (scheduled) · 60 min · **Not crowded** (Recommended)
7. Commuter chooses `108AUP` for comfort and walks to bay.

### Flow 2: Shift / Lecture Planning ("Leave Later")
1. Student selects "Leave at" $\rightarrow$ inputs 08:30 AM tomorrow.
2. Selects "Least crowded" preference.
3. System re-ranks options based on historical 8:30 AM crowding models, surfacing low-crowd alternative routes first.

---

## 3. Screen Inventory & States Matrix

| Screen | Route | Loading State | Empty / No-Result State | Error / Offline State | Primary Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Plan Journey** | `/` | Subtle inline pulse on fields | "No stops found matching '[query]'" | Network warning banner with "Retry" button | **Search** (44px touch height) |
| **Results** | `/results` | Skeleton rows shaped exactly like route cards | "No direct bus route between these stops. Try walking up to 800m to nearby stops." | "We couldn't load results. Check your connection." + [Retry] | Tap row to inspect route on map |
| **Route Details** | `/route/:id` | Skeleton vertical timeline | "Route stops unavailable." | "Unable to load schedule. [Retry]" | Change hour / day type |
| **Network Analytics** | `/analytics` | Skeleton KPI cards and chart blocks | "No data recorded for this selection." | "Data unavailable." | Select time/day filter |
| **Data & Method** | `/about` | Static content, instant load | N/A | N/A | Read methodology |

---

## 4. Plain Language & Microcopy Rules

### A. Jargon Elimination Rules
- **NEVER** display on user-facing screens: `ETM`, `GTFS`, `WAPE`, `MAE`, `Index`, `Zone 0..7`, `Mode A/B/C`, `Composite Score`, `RCI`.
- These technical terms belong exclusively to the **Data & Method (`/about`)** glossary.

### B. Standardized Crowd Level Vocabulary

| API Category | English Plain Label | Hindi Plain Label (हिन्दी) | Meaning to Commuter | Color Token |
| :--- | :--- | :--- | :--- | :--- |
| **Low** | **Not crowded** | **कम भीड़** | Likely to find seats immediately | Green (`#1B7F52`) |
| **Moderate** | **Fairly crowded** | **मध्यम भीड़** | Seats full, plenty of standing space | Amber (`#8A5A00` text) |
| **High** | **Very crowded** | **ज़्यादा भीड़** | High passenger load, limited standing | Red (`#C8372D`) |
| **Insufficient data** | **Not enough data** | **पर्याप्त डेटा नहीं** | Historical data sparse for this hour | Grey (`#5F6B73`) |

### C. Honesty & Historical Qualification
- Show once per results view: *"Based on past ticket data for this time of day"* (हिन्दी: *"दिन के इस समय के पिछले टिकट डेटा पर आधारित"*).
- Timetable departure times must always display the word **"scheduled"** (हिन्दी: *"समय सारिणी"*).
- Model confidence: *"Based on a lot of data"* (High), *"Based on some data"* (Medium), *"Based on little data"* (Low).
- Sentence case everywhere. No exclamation marks, no "Oops!", no emoji.
