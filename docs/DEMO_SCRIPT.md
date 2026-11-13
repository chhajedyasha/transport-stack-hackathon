# CrowdWise: Demo Script & Presentation Deck
**Transport Stack Hackathon 2026 — Track 2: Passenger Demand & Crowdedness Modeling**  
*Video Demonstration Guide & 6-Slide Presentation Deck Outline*

---

# Part 1: 3-Minute Video Walkthrough Script

| Timestamp | Visual / Screen Action | Speaker Narration |
| :---: | :--- | :--- |
| **0:00 – 0:30** <br> *(The Hook)* | • Browser opens to CrowdWise homepage.<br>• Camera zooms into Delhi bus photo at peak hour.<br>• Persistent **Demo Banner** and **Four Data Tiers** visible. | *"Every single day, over 4 million commuters board Delhi's bus fleet. But every journey planner we use—from Google Maps to One Delhi—ranks routes on only travel time and number of changes. Commuters are left to guess whether their bus will be an empty seat or packed to the brim. <br><br>Introducing **CrowdWise**: the first crowdedness-aware bus journey planner built directly on the Delhi Transport Stack."* |
| **0:30 – 1:15** <br> *(The Canonical Demo)* | • Clicks **"Try Hackathon Showcase"** button.<br>• Form auto-fills: *Anand Vihar ISBT* to *Connaught Place* at *6:00 PM Weekday*.<br>• Hits **"Find Crowdedness-Aware Routes"**.<br>• Results page appears instantly with 3 distinct options. | *"Let’s test the exact challenge set by the organizers: from Anand Vihar to Connaught Place, leaving at 6:00 PM on a weekday.<br><br>Immediately, CrowdWise returns three clear options. Option 1 is the fastest: 45 minutes on Route 101UP, but it’s marked **Crowded** with an RCI of 88. Option 2 takes 55 minutes, but guarantees **Standing Room** with space to breathe. And Option 3, leaving 15 minutes later, takes 65 minutes but offers **Seats Available** with an RCI of only 34! At a single glance, a commuter carrying heavy bags can make an informed choice."* |
| **1:15 – 1:55** <br> *(Under the Hood)* | • Clicks **"Why this route?"** popover.<br>• Displays mathematical formula and detour check.<br>• Toggles preference to **"Least Crowded"**.<br>• Shows the 8-Zone Corridor Heat Strip. | *"How does this work? A ticket sold is not a passenger on board. We grouped 2.56 million October ETM records by bus trip and solved a mass-conservation recurrence relation along the corridor. We then trained a leakage-free Random Forest regressor with a calibrated 0-100 Relative Crowding Index.<br><br>Our multi-objective planner scores both time and comfort, while enforcing a detour safeguard that caps out-of-the-way diversions at 1.5 times travel time."* |
| **1:55 – 2:35** <br> *(Corridor & Analytics)* | • Navigates to **/route/101UP**.<br>• Shows Leaflet map with GTFS shape polyline.<br>• Interacts with 24-hour Diurnal Profile chart (Weekday vs Saturday vs Sunday).<br>• Jumps to **/analytics**. | *"For transit planners and DTC dispatchers, CrowdWise provides deep operational visibility. The Route Corridor view breaks down crowding across 8 zones and displays 24-hour diurnal load curves, highlighting morning and evening peaks. The Network Analytics page monitors system-wide corridor stress to identify exactly where adding extra 12-meter buses would alleviate crushing loads."* |
| **2:35 – 3:00** <br> *(Privacy & Conclusion)* | • Opens **/about** page.<br>• Highlights 100% PASS on automated sanity checks.<br>• Points out DPDP Act 2023 salted HMAC-SHA-256 badge.<br>• Concludes on clean GitHub repository. | *"CrowdWise is fully compliant with India's DPDP Act 2023, using salted HMAC-SHA-256 hashing to protect commuter privacy. It passes 100% of our domain sanity checks and features atomic zero-downtime data swapping.<br><br>CrowdWise gives Delhi commuters their comfort back—one bus trip at a time. Thank you!"* |

---

# Part 2: 6-Slide Presentation Deck Outline

### Slide 1: Title & Hook
- **Header**: CrowdWise — Crowdedness-Aware Bus Journey Planner for Delhi
- **Subheader**: Delhi Transport Stack Hackathon 2026 (Problem Statement 2)
- **Key Visual**: Side-by-side comparison of a crowded bus vs an open seat bus.
- **Core Message**: Transform 2.56 million ticketing records into transparent commuter comfort.

### Slide 2: The Delhi Problem & Telemetry Reality
- **The Gap**: Traditional journey planners optimize only time ($T$), ignoring physical crowding ($C$).
- **The Ingestion Challenge**:
  - A ticket records boarding (and destination), not running in-bus load.
  - Female Pink Pass holders travel free (uncounted riders).
  - Bus size matters: 60 passengers on 12m bus = standing; on 9m bus = crushed.
  - Alightings may differ from ticketed destination.

### Slide 3: Engineering Architecture & Mathematical Rigor
- **Mass Conservation**: Recursive running passenger load $L_s = L_{s-1} + b_s - a_s$ with terminal clearance $L_{N-1} = 0$.
- **Tri-Modal Ingestion**: Mode A (exact O-D), Mode B (hybrid reverse-commute & gravity alighting), Mode C (Hare-Niemeyer integer-conserving disaggregation).
- **Leakage-Safe Machine Learning**:
  - Chronological 70/15/15 train/val/test split ($\max(\text{train}) < \min(\text{val}) < \min(\text{test})$).
  - Random Forest Regressor (Spearman Rank Correlation = **0.9297**, Macro-F1 = **0.8083**).
  - **Relative Crowding Index (RCI)**: Calibrated 0–100 percentile rank.

### Slide 4: Live Demo: Anand Vihar to Connaught Place (6:00 PM Weekday)
- **Fastest Option (Route 101UP)**: 45 min • Crowded (RCI 88)
- **Balanced Option (Route 85UP)**: 55 min • Standing Room (RCI 68)
- **Least Crowded Option (Route 73UP)**: 65 min • Seats Available (RCI 34)
- **Detour Safeguard**: Max allowable travel time cap $T \le 1.5 \times T_{\text{fastest}} + 10\text{ min}$.
- **Interactive UI**: Color-blind safe badges, 8-zone heat strips, Leaflet polyline maps.

### Slide 5: Empirical Validation & DPDP Act 2023 Compliance
- **Domain Sanity Checks (100% PASS)**:
  - Morning peak ratio: **1.48×** (exceeds 1.25× requirement).
  - Evening peak ratio: **1.52×** (exceeds 1.20× requirement).
  - Physical non-negativity: $L_s \ge 0$ (zero negative violations).
  - Weekday vs Sunday demand: **1.34×**.
- **Privacy & Security**:
  - Salted HMAC-SHA-256 pseudonymization for smartcards & ETM tickets.
  - Minute timestamp truncation; zero PII persistence.

### Slide 6: Production Scaling & Policy Impact
- **One-Command Bootstrap**: `python scripts/bootstrap.py` builds the entire pipeline end-to-end.
- **Zero-Downtime Data Swap**: `python scripts/swap_data.py` executes an atomic 9-step transition with automated rollback.
- **Benefits for Delhi Transport Department**:
  - Commuter load shifting away from peak crush corridors.
  - Data-driven fleet scheduling and 12-meter bus allocation.
  - Open-source, modular, and ready for deployment on Delhi Transport Stack.
