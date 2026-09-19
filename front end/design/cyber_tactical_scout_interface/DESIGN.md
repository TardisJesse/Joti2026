---
name: Cyber Tactical Scout Interface
colors:
  surface: '#031426'
  surface-dim: '#031426'
  surface-bright: '#2b3a4e'
  surface-container-lowest: '#000f20'
  surface-container-low: '#0c1c2e'
  surface-container: '#102033'
  surface-container-high: '#1b2b3e'
  surface-container-highest: '#263649'
  on-surface: '#d3e4fd'
  on-surface-variant: '#b9cacb'
  inverse-surface: '#d3e4fd'
  inverse-on-surface: '#223144'
  outline: '#849495'
  outline-variant: '#3b494b'
  surface-tint: '#00dbe9'
  primary: '#dbfcff'
  on-primary: '#00363a'
  primary-container: '#00f0ff'
  on-primary-container: '#006970'
  inverse-primary: '#006970'
  secondary: '#d7ffc5'
  on-secondary: '#053900'
  secondary-container: '#2ff801'
  on-secondary-container: '#0f6d00'
  tertiary: '#fff4e8'
  on-tertiary: '#412d00'
  tertiary-container: '#ffd386'
  on-tertiary-container: '#7d5800'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#7df4ff'
  primary-fixed-dim: '#00dbe9'
  on-primary-fixed: '#002022'
  on-primary-fixed-variant: '#004f54'
  secondary-fixed: '#79ff5b'
  secondary-fixed-dim: '#2ae500'
  on-secondary-fixed: '#022100'
  on-secondary-fixed-variant: '#095300'
  tertiary-fixed: '#ffdea8'
  tertiary-fixed-dim: '#ffba20'
  on-tertiary-fixed: '#271900'
  on-tertiary-fixed-variant: '#5e4200'
  background: '#031426'
  on-background: '#d3e4fd'
  surface-variant: '#263649'
typography:
  display-hero:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-hero-mobile:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: '0'
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: '0'
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: 0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.04em
  label-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.06em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.25rem
  space-2xl: 3.5rem
---

## Brand & Style

This design system blends deep-ops tactical cyber warfare aesthetics with the approachable, mischievous energy of scouting lore (exemplified by the 'Allart-eendje' rubber duck mascot). It serves youth scouts engaged in high-stakes nocturnal hacking missions, field cryptography, and network infiltration games.

The visual direction merges **Retro/Cyberpunk Tactical HUD** with high-contrast accessibility engineered for outdoor readability in varying light conditions—from pitch-black forest nights to flickering campfires and cold mobile screens:
- **Atmosphere:** Dark net operations center, immersive field terminal, gamified covert mission tracker.
- **Tone:** Electrifying, mission-critical, playful yet formidable, highly utilitarian.
- **Visual Dialect:** Fine cyber-mesh background grids, subtle neon luminescence, translucent glass panels with tech-spec 1px cyan hairline strokes, scanline noise, and angular telemetry data points paired with friendly rubber-duck Easter eggs.

## Colors

The palette establishes an ultra-deep void baseline, making neon telemetry lines and signals instantly legible without overwhelming night vision.

### Palette Architecture
- **Primary (`#00F0FF` - Electric Cyber Cyan):** Primary tactical actions, HUD focus rings, directional network nodes, telemetry scans.
- **Secondary (`#39FF14` - Terminal Matrix Green):** Active console text, successful decryption states, live pings, scouting trail checkpoints.
- **Tertiary (`#FFB800` - Neon Amber):** Mission alerts, time-decay warnings, reconnaissance markers, mascot gold highlights.
- **Alert / Destructive (`#FF0055` - Glitch Neon Coral):** System breach, failed override, enemy drone proximity alerts.
- **Base Surfaces:**
  - Canvas Void: `#070B14`
  - Container Base: `#0D1322`
  - Container Raised / Panel: `#131C31`
  - Subsurface / Card Hover: `#1C2945`
- **Text Tiers:**
  - High-Contrast Terminal: `#FFFFFF` (Primary headlines, critical readout)
  - Radar Slate: `#8E9EB5` (Secondary descriptors, metadata, inactive labels)
  - Terminal Echo: `#39FF14` (Inline code snippets, telemetry coordinates)

## Typography

Typography strikes a functional balance between terminal instrumentation and high-efficiency scanning:
- **Headlines (Space Grotesk):** Delivers aerodynamic, futuristic contours without sacrificing legibility at large and medium scales.
- **Body Text (Inter):** Ensures clear, fatigue-free reading of mission briefing logs, decoding rules, and lore passages under low-brightness device screens.
- **Labels & Tactical HUD Readouts (JetBrains Mono):** Monospaced precision for IP addresses, GPS coordinates, countdown clocks, encryption keys, and badge markers. All monospaced labels default to uppercase for a strict military-recon feel.

## Layout & Spacing

Field hacking games require rapid single-thumb operations on mobile while navigating uneven terrain, as well as dense multi-window command dashboards for the game-master base camp.

### Layout Model
- **Grid Architecture:** 4-column layout on mobile, 8-column on tablet, 12-column on desktop with max container width constrained to `1280px` for situational awareness.
- **Touch Targets:** Outdoor ergonomics mandate a minimum interactive touch target of `48px` (ideally `56px` for primary hack interactions) to accommodate cold fingers or gloves.
- **Background Layering:** A fixed CSS vector grid (24px cell size, `#00F0FF` at 3% opacity) sits atop `#070B14`, creating depth behind tactical radar and card components.

## Elevation & Depth

Visual hierarchy is constructed through tonal stratification, subtle neon emissions, and translucent HUD membranes rather than traditional drop shadows.

- **Level 0 (Void Ground):** Background `#070B14` with subtle radial gradient flares in cyan or lime at coordinates of interest.
- **Level 1 (Subsurface Module):** Background `#0D1322` with 1px border colored `#00F0FF` at 15% opacity.
- **Level 2 (Active HUD Card):** Background `rgba(19, 28, 49, 0.85)` with backdrop blur of `12px`, 1px border colored `#00F0FF` at 30% opacity, and an ambient cyber glow: `0 0 16px rgba(0, 240, 255, 0.08)`.
- **Level 3 (Tactical Float / Modal / Target Lock):** Background `rgba(19, 28, 49, 0.95)`, 1px border `#00F0FF` at 60% opacity, accented by dual glow: `0 0 24px rgba(0, 240, 255, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.1)`.
- **Alert Elevation:** Red/amber state overrides introduce equivalent colored outer glows (`rgba(255, 0, 85, 0.25)` or `rgba(255, 184, 0, 0.2)`).

## Shapes

The shape system adopts a hybrid aesthetic: comfortable `rounded-2xl` (16px) perimeter geometry for card containers and dialog surfaces, contrasting with technical chamfers and tighter `rounded-md` (6px) chips and badges. 

This juxtaposition preserves modern app fluidity and touch comfort while staying true to military terminal hardware. Avatars, status diodes, and radar rings remain pure circles (`rounded-full`).

## Components

### Buttons
- **Primary Action (Execute Hack / Deploy Node):** Electric Cyan fill (`#00F0FF`), text `#070B14` in JetBrains Mono 600 uppercase, `rounded-xl`, min-height 52px. Hover triggers a bright cyan bloom (`0 0 20px rgba(0, 240, 255, 0.4)`). Active state applies a scale transform of `0.98`.
- **Secondary (Bypass / Inspect):** Transparent surface, 1px border `#00F0FF` at 40% opacity, text `#00F0FF`. Hover initiates a matrix green border flash and surface fill of `rgba(0, 240, 255, 0.08)`.
- **Danger (Abort / System Wipe):** Glitch Coral border (`#FF0055`), text `#FF0055`, red alert glow on hover.

### Status Chips & Badges
- **Configuration:** Monospace uppercase labels (`label-mono-sm`), `rounded-md` (6px), padding `4px 10px`.
- **Variants:**
  - *Online / Secured:* `#39FF14` background at 10% opacity, 1px border `#39FF14` at 40%, text `#39FF14` with a pulsing 6px round green LED indicator.
  - *Jamming / Intercepted:* `#FFB800` background at 10% opacity, 1px border `#FFB800` at 40%, text `#FFB800`.
  - *Compromised:* `#FF0055` background at 12%, border `#FF0055` at 50%, text `#FF0055`.

### Cards & Tactical Panels
- Structure: Rounded-2xl (`1rem` / 16px radius), `rgba(13, 19, 34, 0.9)` backdrop blur, framed with a precise 1px stroke of `#00F0FF` at 25-30% opacity.
- Header: Monospace sub-caption with tactical bracket notation (e.g. `[SEC-NODE // 04]`) accompanied by the scouting duck mini-sigil.

### Input Fields
- **Terminal Inputs:** Dark recessed background `#070B14`, 1px border `#8E9EB5` at 30%, text `#FFFFFF` (typed text in JetBrains Mono). 
- **Focus State:** 1px border `#00F0FF`, field outline glow `0 0 12px rgba(0, 240, 255, 0.25)`. Includes a blinking cyan caret (`|`).

### Checkboxes & Radios
- Square with slightly rounded corners (checkbox, 4px radius) or circular (radio), 20x20px dimension.
- Inactive: 1.5px border `#8E9EB5` at 40%, background transparent.
- Checked: `#00F0FF` border and fill, with `#070B14` checkmark icon or solid center dot, surrounded by subtle cyan luminescence.

### Mascot Integration & Radar Displays
- **Allart-eendje HUD Avatar:** Rubber duck icon rendered in high-contrast vectorized neon line art (`#FFB800` with cyan visor goggles).
- **Radar Compass / Sweep:** Concentric rings in cyan at 10% and 20% opacity with rotating sweep gradient (`conic-gradient(from 0deg, transparent 0deg, rgba(0, 240, 255, 0.2) 360deg)`), highlighting scout waypoint blips.