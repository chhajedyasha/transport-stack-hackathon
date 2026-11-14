# MANUAL_TODO.md — Owner Action Checklist

This document details the exact items that require manual owner intervention, why they are needed, and the autonomous fallback in place.

---

## Summary: What the System Handles vs. What the Owner Needs to Do

| Category | What the System Does (100% Complete) | What YOU (Owner) Need to Do |
|---|---|---|
| **Code & Architecture** | 100% complete (Frontend, Backend, ML, Scripts) | None |
| **GTFS Static Data** | Ingested full official Delhi GTFS (6,862 stops, 2,574 routes) | None |
| **Ticketing Data** | Ingested 2,559,899 October ETM records into 3.32M facts | None |
| **Model Retraining** | Retrained Random Forest (34.4 MB) & RCI Calibrator | None |
| **Testing & Sanity** | 100% automated pytest (348/348), smoke tests, & sanity checks | None |
| **Submission Pack** | Drafted 2-page Proposal (`docs/PROPOSAL.md`, `PROPOSAL.html`), Technical Note (`docs/TECHNICAL_NOTE.md`), and 3-minute video script (`docs/DEMO_SCRIPT.md`) | Review, record 3-min video, & submit on portal |
| **Deployment Prep** | Configured for local running, Docker, Vercel, and Render | Optional: add cloud credentials if hosting live |

---

## Action Items for Owner (Submission Checklist)

### 1. What is the "Proposal" and What Do You Submit?
- **What it is:** The hackathon portal asks teams to submit a formal **written proposal / technical brief** explaining your approach to Problem Statement 2 (Crowdedness-Aware Bus Journey Planner).
- **Status:** We have written a comprehensive, rigorous proposal ready for you:
  - Markdown version: [`docs/PROPOSAL.md`](file:///c:/Users/rajsi/OneDrive/Desktop/Documents/raj/transport  hackathon/transport-stack-hackathon/docs/PROPOSAL.md)
  - Styled HTML/PDF-ready version: [`docs/PROPOSAL.html`](file:///c:/Users/rajsi/OneDrive/Desktop/Documents/raj/transport  hackathon/transport-stack-hackathon/docs/PROPOSAL.html)
  - Technical methodology note: [`docs/TECHNICAL_NOTE.md`](file:///c:/Users/rajsi/OneDrive/Desktop/Documents/raj/transport  hackathon/transport-stack-hackathon/docs/TECHNICAL_NOTE.md)
- **Your Action:** Open `docs/PROPOSAL.md` (or open `docs/PROPOSAL.html` in your browser and print to PDF), add your team name and member details, and upload it to the hackathon submission form.

### 2. What is the "3-Minute Video Script"?
- **What it is:** The hackathon organizers typically require a short **3-minute screen recording / video walkthrough** showing that your application actually works, takes user input, shows crowdedness levels, and explains the trade-offs.
- **Status:** We prepared [`docs/DEMO_SCRIPT.md`](file:///c:/Users/rajsi/OneDrive/Desktop/Documents/raj/transport  hackathon/transport-stack-hackathon/docs/DEMO_SCRIPT.md), which gives you:
  - Exact second-by-second timestamps (0:00 to 3:00).
  - Exact buttons to click on screen (e.g. Anand Vihar to Connaught Place at 18:00, toggling "Least Crowded", viewing route corridor, viewing network analytics).
  - Word-for-word voiceover script so you don't have to stumble or guess what to say.
- **Your Action:**
  1. Start the backend (`python backend/run.py`) and frontend (`npm run dev` in `frontend/`).
  2. Open OBS Studio, Loom, or Windows Game Bar (`Win + Alt + R`).
  3. Follow `docs/DEMO_SCRIPT.md` to click through the pages while reading the script.
  4. Upload the video to YouTube (unlisted) or Google Drive, and paste the link into the submission form.

### 3. Official Organizer Dataset Status
- **Status:** **PROCESSED, RETRAINED & 100% ACTIVE IN PRODUCTION**.
- **Dataset:** `data/raw/organizer/October-Delhi.csv` (2,559,899 ETM tickets, 31 full days of October 2026).
- **Execution:** 3,322,312 corridor zone demand facts seeded in `backend/crowdwise.db`.
- **Model:** Random Forest regressor (34.4 MB) retrained on 2.22M train rows, verified on 672k held-out test rows, RCI calibrated 0–100.
- **Provenance:** `data_mode = 'organizer'`, `active_tier = 'organizer'`. Zero synthetic data.

### 4. Vehicle Capacity & Pink Pass Assumptions
- **Configured Values:**
  - Standard bus capacity: 60 passengers (40 seated + 20 standing).
  - Pink Pass expansion factor: $\gamma_r = 1.30$ (accounts for Delhi's free travel scheme for women, representing ~30% of actual ridership).
- **Your Action:** If organizers specify custom bus capacity rosters, you can edit `config/capacity_by_bus_type.yaml`. Otherwise, the current documented assumptions are standard for DTC 12-meter CNG low-floor buses.

### 5. Git & Code Protection Reminder
- The GitHub remote is `https://github.com/rajnyx/transport-stack-hackathon.git` (`main` branch).
- All raw CSV and GTFS data files are preserved safely in `data/raw/`.
- Ensure your GitHub repository visibility matches organizer guidelines before submission.

### 6. Native Speaker Review of Hindi Translations (`frontend/src/i18n/hi.json`)
- **Status:** **DRAFTED & ACTIVE IN APPLICATION**.
- **Scope:** Complete bilingual UI dictionaries (`frontend/src/i18n/hi.json` and `en.json`).
- **Standardized Crowd Labels:**
  - Low $\rightarrow$ कम भीड़
  - Moderate $\rightarrow$ मध्यम भीड़
  - High $\rightarrow$ ज़्यादा भीड़
  - Insufficient data $\rightarrow$ पर्याप्त डेटा नहीं
  - Timetable scheduled $\rightarrow$ निर्धारित समय
  - Historical data line $\rightarrow$ इस समय के पिछले टिकट डेटा पर आधारित
- **Your Action:** Have a native Hindi speaker do a final proofread of `frontend/src/i18n/hi.json` to ensure colloquial phrasing aligns with everyday Delhi commuter usage. Do not claim it is natively reviewed until inspected.
