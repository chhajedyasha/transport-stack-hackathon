# CrowdWise — Public Transit Design System

**Version:** 3.0 (Public Transit Edition)  
**Authority:** Principal Product Designer & Senior Frontend Engineer  
**Token Source:** `frontend/src/styles/tokens.css` $\rightarrow$ `frontend/tailwind.config.js`

---

## 1. Core Principles
1. **Tool First:** The interface is an instant public transport utility, not a marketing portal. No heroes, no taglines, no floating blobs.
2. **Obvious & Calm:** Designed for one-handed operation on a 360px budget Android phone in blinding Delhi sunlight.
3. **Factual Honesty:** Never hides data provenance; shows "scheduled" on timetables; labels historical predictions clearly; shows "Not enough data" on low confidence.
4. **Accessible Contrast:** Body text and all critical transit numerals (departure times, durations, crowd status) maintain $\ge 7:1$ contrast against their backgrounds.

---

## 2. Color Palette & Accessibility Tokens

| Token Name | Hex Value | Semantic Usage | Minimum Contrast |
| :--- | :--- | :--- | :--- |
| `navy` (`--color-navy`) | `#142B3B` | Brand identity, primary headings, Route Badge background | 13.5:1 on `#FFFFFF` |
| `navy-dark` (`--color-navy-dark`) | `#0E1F2B` | Hover states on navy controls | 16.2:1 on `#FFFFFF` |
| `teal` (`--color-teal`) | `#147D78` | Primary interactive buttons, active tab indicators, links | 4.8:1 on `#FFFFFF` |
| `teal-hover` (`--color-teal-hover`) | `#106662` | Hover state for primary action buttons | 6.2:1 on `#FFFFFF` |
| `teal-tint` (`--color-teal-tint`) | `#E8F4F3` | Active row background tint, selection pill background | 1.15:1 (Background) |
| `background` (`--color-background`) | `#F7F8F6` | Calming non-glare app canvas background | Canvas base |
| `surface` (`--color-surface`) | `#FFFFFF` | Transit cards, sheets, form panels, dropdown menus | Surface base |
| `border` (`--color-border`) | `#DDE2E3` | Crisp 1px structural dividing lines | 1.3:1 (Structural) |
| `text` (`--color-text`) | `#202A32` | Primary readable copy, stop names, journey durations | 14.1:1 on `#FFFFFF` ($\ge 7:1$) |
| `text-muted` (`--color-text-muted`) | `#5F6B73` | Secondary metadata (scheduled label, platform info) | 5.2:1 on `#FFFFFF` ($\ge 4.5:1$) |

### Crowdedness Color Calibration
Every crowd level uses a 3-part representation: **Color + Text Label + Segmented Meter**. Never color alone.

| Level | Fill Color | Text Color | Tint Background | Plain English | Plain Hindi (हिन्दी) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Low** | `#1B7F52` | `#1B7F52` | `#EAF6EE` | **Not crowded** | **कम भीड़** |
| **Moderate** | `#F2B01E` | `#8A5A00` | `#FEF7E8` | **Fairly crowded** | **मध्यम भीड़** |
| **High** | `#C8372D` | `#C8372D` | `#FBEBE9` | **Very crowded** | **ज़्यादा भीड़** |
| **Unknown** | `#8A949B` | `#5F6B73` | `#F1F3F4` | **Not enough data** | **पर्याप्त डेटा नहीं** |

*Note on Moderate text:* Text on amber/moderate backgrounds is strictly darkened to `#8A5A00` to exceed the WCAG 4.5:1 contrast requirement (achieving 5.1:1).

---

## 3. Typography & Numerals

* **Primary Font:** Inter (System fallback: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
* **Devanagari Font:** Noto Sans Devanagari (System fallback: `"Mangal", "Nirmala UI", sans-serif`).
* **Typographic Scale:**
  - `32px` (`text-2xl` / `h1`): Main screen titles only.
  - `24px` (`text-xl` / `h2`): Section question headings.
  - `20px` (`text-lg` / `h3`): Large duration minutes (e.g., `42 min`).
  - `16px` (`text-base`): Default body text, stop names, input values.
  - `14px` (`text-sm`): Secondary metadata, timetables, badges.
  - `12px` (`text-xs`): Provenance lines, timestamps (never smaller than 12px).
* **Weights:** 400 (Regular), 500 (Medium), 600 (Semibold) only.
* **Tabular Numerals:** All transit times, countdowns, durations, and percentages apply `.tabular-nums` (`font-variant-numeric: tabular-nums`).

---

## 4. Spacing, Shapes, and Elevation

* **Base Grid:** 4px base with 8px rhythm (`gap-2`, `p-3`, `p-4`, `py-3`).
* **Corner Radius:**
  - `4px` (`rounded-control`): Buttons, text inputs, combobox dropdowns.
  - `6px` (`rounded-panel`): Form container panels, popovers, bottom sheet.
  - `9999px` (`rounded-chip`): RouteBadge and CrowdStrip pills only.
  - *Rule:* Zero `rounded-xl`, `rounded-2xl`, or `rounded-3xl` anywhere.
* **Elevation & Shadows:**
  - Standard cards and list rows have `shadow-none` and rely strictly on `1px solid var(--color-border)`.
  - Floating overlays (combobox autocomplete list, mobile bottom sheet) use single subtle elevation: `0 4px 16px rgba(20, 43, 59, 0.08)`.

---

## 5. Motion Tokens
* **Durations:** 120ms (micro-interactions, button hover), 200ms (dropdowns, expanders), 280ms (bottom sheet snap transitions).
* **Easing:** `cubic-bezier(0.2, 0, 0, 1)` (standard ease-out).
* **Rule:** Animated properties are strictly restricted to `transform` and `opacity`. Respects `prefers-reduced-motion`.

---

## 6. Signature Primitives (At Most 14 Components)
1. `Button` (Primary / Secondary / Ghost, min 44px touch height)
2. `TextField` (Clear label, high contrast border, 2px teal focus ring)
3. `StopCombobox` (Search with Recent, Nearby, Highlighted matches, Debounced 150ms)
4. `DateTimeField` (Custom accessible popover, no unstyled raw browser picker)
5. `SegmentedControl` (Fastest / Balanced / Least crowded toggle)
6. `RouteBadge` (Navy rectangle `#142B3B`, white bold tabular route number)
7. `CrowdStrip` (3-segment horizontal bar + plain-language crowd label)
8. `TimeBreakdownBar` (Proportional walk / wait / ride inline visual bar)
9. `TransitRow` (Dense list row with RouteBadge, departure time, duration, crowd)
10. `CompareTable` (Sticky first column comparison of top 3 alternatives)
11. `Panel` (Border-only container)
12. `BottomSheet` (Mobile 3-snap-point sheet: peek, half, full)
13. `Skeleton` (Shaped exactly to match row layouts, no blank flash)
14. `EmptyErrorState` (Plain language explanation + clear actionable Retry)
