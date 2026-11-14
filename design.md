---
version: alpha
name: Transit Playful Utility
description: A bright, optimistic transit brand with bold friendly typography, sky-like pastels, and minimal chrome.
colors:
  primary: "#12452B"
  primary-60: "#2F6B48"
  secondary: "#00B8B5"
  tertiary: "#FFA800"
  accent: "#A800B0"
  background: "#FDF5F2"
  surface: "#FFFFFF"
  neutral: "#E5E7EB"
  on-surface: "#12452B"
  on-primary: "#FFFFFF"
  error: "#E53935"
  info: "#1DA1F2"
typography:
  headline-display:
    fontFamily: "Puffin Transit ExtraBold, sans-serif"
    fontSize: 72px
    fontWeight: 800
    lineHeight: 72px
    letterSpacing: 0px
  headline-lg:
    fontFamily: "Puffin Transit ExtraBold, sans-serif"
    fontSize: 60px
    fontWeight: 800
    lineHeight: 60px
    letterSpacing: 0px
  headline-md:
    fontFamily: "Puffin Transit ExtraBold, sans-serif"
    fontSize: 40px
    fontWeight: 800
    lineHeight: 48px
    letterSpacing: 0px
  headline-sm:
    fontFamily: "Puffin Transit Regular, sans-serif"
    fontSize: 24px
    fontWeight: 400
    lineHeight: 32px
    letterSpacing: 0px
  body-lg:
    fontFamily: "Puffin Transit Regular, sans-serif"
    fontSize: 24px
    fontWeight: 400
    lineHeight: 32px
    letterSpacing: 0px
  body-md:
    fontFamily: "Puffin Transit ExtraBold, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0px
  body-sm:
    fontFamily: "Puffin Transit ExtraBold, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 18px
    letterSpacing: 0px
  label-lg:
    fontFamily: "Puffin Transit SemiBold, sans-serif"
    fontSize: 16px
    fontWeight: 600
    lineHeight: 20px
    letterSpacing: 0px
  label-md:
    fontFamily: "Puffin Transit SemiBold, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 18px
    letterSpacing: 0px
  label-sm:
    fontFamily: "Puffin Transit SemiBold, sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 16px
    letterSpacing: 0px
  caption:
    fontFamily: "Puffin Transit Regular, sans-serif"
    fontSize: 11px
    fontWeight: 400
    lineHeight: 14px
    letterSpacing: 0px
  serif-body:
    fontFamily: "Lora, serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0px
  serif-strong:
    fontFamily: "Lora, serif"
    fontSize: 18px
    fontWeight: 700
    lineHeight: 26px
    letterSpacing: 0px
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 16px
  xl: 24px
  full: 9999px
spacing:
  xs: 12px
  sm: 20px
  md: 32px
  lg: 46px
  xl: 160px
components:
  button-primary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.full}"
    padding: "14px 24px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.primary-60}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
    padding: "14px 24px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.full}"
    padding: "12px 22px"
    height: "40px"
  button-tertiary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.none}"
    padding: "0px"
  card:
    backgroundColor: "{colors.background}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: "12px 16px"
    height: "40px"
  chip:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
    padding: "6px 10px"
  badge:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.full}"
    padding: "4px 8px"
---

# Transit Playful Utility

## Overview
Transit feels cheerful, public-facing, and highly memorable, with a playful editorial voice rather than a corporate one. The visual tone is airy and optimistic: soft sky gradients, bright accent colors, and oversized rounded typography create a sense of motion and ease. The interface is spacious and promotional, designed to inspire confidence and curiosity in a broad consumer audience.

## Colors
- **Primary (#12452B):** Deep transit green used for body text, navigation, and the most important dark UI accents. It grounds the brand and gives contrast against the pale background.
- **Secondary (#00B8B5):** A vivid teal used for strong action states and brand-forward UI moments. It reads as energetic and modern, especially on buttons.
- **Tertiary (#FFA800):** A warm golden yellow used for highlights, callouts, and attention-grabbing details. It brings the illustration-heavy layout to life without feeling harsh.
- **Accent (#A800B0):** A saturated magenta-purple used sparingly for route markers, pins, and playful micro-accents. It adds variety and reinforces the brand’s travel-map feel.
- **Background (#FDF5F2):** A soft warm off-white that keeps the page open and airy. It prevents the colorful illustrations from feeling overpacked.
- **Surface (#FFFFFF):** Clean white for cards, bubbles, and content panels that need separation from the background. It supports the light, luminous look.
- **Neutral (#E5E7EB):** A light border and divider tone used when structure is needed without visual weight. Borders stay subtle rather than prominent.
- **On-surface (#12452B):** The default readable text color on light surfaces. It carries most of the typographic hierarchy.
- **On-primary (#FFFFFF):** White text for filled action buttons and bright color blocks. It preserves clarity over saturated fills.
- **Error (#E53935):** Reserved for urgent alerts and destructive actions if needed. It should remain rare in this optimistic system.
- **Info (#1DA1F2):** A transit-map blue used for wayfinding, markers, and route-like graphics. It complements the teal and magenta accents well.

## Typography
The system is dominated by the custom Puffin Transit family, which gives the brand its rounded, friendly, highly recognizable personality. Headlines use very heavy weights and tight line heights, producing a bold poster-like feel; body copy stays in the same family for consistency, but with smaller sizes and looser line heights for readability. Lora is available for editorial or long-form moments, adding a serif contrast when the layout needs a more human, narrative tone.

Use `headline-display`, `headline-lg`, and `headline-md` for hero messaging and major section titles. `headline-sm`, `label-lg`, `label-md`, and `label-sm` should handle navigation, buttons, and small interface text with a compact, confident rhythm. The source does not rely on uppercase styling or wide tracking; the emphasis comes from weight, size, and color contrast instead.

## Layout
The layout is centered and expansive, with a wide hero composition that leaves generous negative space around the primary message. Content appears to sit within a fluid, desktop-first frame rather than a strict boxed grid, with illustrations anchoring the lower corners and the headline centered above them. Spacing is intentionally large: use the `xs` through `xl` scale to preserve the airy, poster-like feel and avoid compressing the composition.

Section padding should feel generous, with large top and bottom breathing room and medium spacing between headline, body copy, and CTA. Cards and smaller content blocks can use tighter internal padding, but outer page sections should remain spacious to keep the brand light and open. Avoid dense multi-column packing unless the content is clearly secondary.

## Elevation & Depth
The system is mostly flat, with minimal shadow usage and little reliance on layered depth. Hierarchy comes from contrast, color blocking, and scale rather than heavy elevation effects. When depth is needed, it should be subtle and playful: soft shadowing on buttons, clear borders on cards, and illustrated overlaps that suggest motion without making the interface feel heavy.

Cards use light borders and pale fills rather than strong drop shadows. Surfaces should generally sit close to the background, with separation achieved through white fills, border lines, and strong typography. Reserve stronger contrast for calls to action and map-like visual elements.

## Shapes
The shape language is rounded and friendly, with a strong preference for pill-like buttons and soft-corner cards. Interactive elements feel approachable rather than technical, and the `full` radius is a core part of the brand’s identity. Use `sm` and `md` only where functional structure is needed; larger radii better match the whimsical transit illustration style.

Avoid sharp corners on primary actions and badges unless a component is explicitly meant to feel utilitarian. The overall silhouette should feel soft, buoyant, and mobile-friendly.

## Components
Buttons should be bold, simple, and highly legible. `button-primary` is the main CTA style: filled `secondary`, rounded `full`, with compact vertical padding and strong contrast text. `button-primary-hover` can darken or deepen the fill, but should stay within the same bright family. `button-secondary` should use a light or transparent treatment with a clear border or tonal distinction, while `button-tertiary` should remain text-only and understated for secondary navigation or inline actions.

Cards (`card`) should use the warm background tone, a subtle `neutral` border, and `rounded.lg` corners. Keep card padding modest at 16px so content remains structured but not boxed in. Cards should feel like quiet containers rather than raised panels.

Inputs should stay clean and functional: white fill, soft border, `rounded.md`, and clear text color. Focus states should be obvious through color or border emphasis rather than shadows. Keep input height comfortable and aligned with button rhythm.

Chips and badges should use saturated accent colors and high corner radius to feel playful and map-like. They should be compact, readable, and easy to scan at a glance. If used in lists or route summaries, keep them visually lightweight and avoid overly complex ornamentation.

## Do's and Don'ts
- Do keep primary actions large, rounded, and high-contrast.
- Do preserve generous whitespace around major headlines and hero illustrations.
- Do use bold typography for emphasis instead of heavy shadows or complex effects.
- Do keep borders subtle and use tonal contrast for structure.
- Don't introduce sharp-cornered controls into the main UI pattern.
- Don't overcrowd the layout with too many cards or columns.
- Don't overuse the accent purple or gold; they should punctuate, not dominate.
- Don't rely on deep elevation or glassmorphism to create hierarchy.
