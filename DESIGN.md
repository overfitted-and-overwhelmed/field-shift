---
name: AGRIscora
description: Crop-rotation dashboard for one irrigated Kansas field, dark field green by default with a light theme.
colors:
  field-ground: "#12231a"
  field-panel: "#1a3024"
  field-raise: "#223a2c"
  field-sunk: "#152a1f"
  hairline: "#2e4a3a"
  hairline-strong: "#426350"
  ink: "#ecf2ec"
  ink-2: "#b8c9bc"
  ink-3: "#8fa697"
  primary: "#ecf2ec"
  on-primary: "#12231a"
  primary-hover: "#ffffff"
  good: "#7ad48f"
  bad: "#f4917f"
  warn: "#f2c14e"
  water: "#6fb2ee"
  rain: "#a7cbe6"
  heat: "#f08a4b"
  cold: "#7fb0f0"
  nitro: "#c9b6ff"
  crop-corn: "#e8b23a"
  crop-soybean: "#5dbb63"
  crop-winter-wheat: "#a58be0"
  crop-sorghum: "#e07a45"
  crop-sunflower: "#3cc4a0"
  crop-triticale: "#e58aae"
  band-label-ink: "#10200f"
  light-ground: "#f2f5f0"
  light-panel: "#ffffff"
  light-raise: "#eaf0e8"
  light-sunk: "#f6f8f5"
  light-hairline: "#d5dfd3"
  light-hairline-strong: "#b4c4b2"
  light-ink: "#13251a"
  light-ink-2: "#43574a"
  light-ink-3: "#5f7366"
  light-primary: "#1f5136"
  light-on-primary: "#ffffff"
  light-primary-hover: "#163d28"
  light-good: "#1d7a39"
  light-bad: "#b3261e"
  light-warn: "#8a5d00"
  light-water: "#2b6cb0"
  light-rain: "#5b8db8"
  light-heat: "#c2410c"
  light-cold: "#2563eb"
  light-nitro: "#6d4fc2"
  light-crop-corn: "#d9980b"
  light-crop-soybean: "#2e8b3a"
  light-crop-winter-wheat: "#6f55b8"
  light-crop-sorghum: "#c8551e"
  light-crop-sunflower: "#13917a"
  light-crop-triticale: "#d2668f"
typography:
  display:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  brand:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.3
  title:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  body-sm:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "tnum"
rounded:
  swatch: "3px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.title}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.field-panel}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "38px"
  button-secondary-hover:
    backgroundColor: "{colors.field-raise}"
  button-sm:
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "32px"
  icon-button:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.md}"
    size: "36px"
  icon-button-hover:
    backgroundColor: "{colors.field-raise}"
    textColor: "{colors.ink}"
  select:
    backgroundColor: "{colors.field-sunk}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "40px"
  tab:
    textColor: "{colors.ink-2}"
    typography: "{typography.title}"
    padding: "0 16px"
    height: "60px"
  tab-selected:
    textColor: "{colors.ink}"
  panel:
    backgroundColor: "{colors.field-panel}"
    rounded: "{rounded.xl}"
    padding: "18px 22px"
  segmented:
    backgroundColor: "{colors.field-sunk}"
    rounded: "{rounded.lg}"
    padding: "3px"
  segmented-selected:
    backgroundColor: "{colors.field-panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  crop-toggle:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "38px"
  crop-toggle-on:
    backgroundColor: "{colors.field-panel}"
    textColor: "{colors.ink}"
  crop-chip:
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 12px"
    height: "32px"
  rotation-tag:
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 8px"
    height: "22px"
  rotation-tag-yours:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.field-ground}"
  info-popover:
    backgroundColor: "{colors.field-panel}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.lg}"
    width: "320px"
  tooltip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.field-ground}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "6px 9px"
---

# Design System: AGRIscora

## Overview

**Creative North Star: "The Field Office"**

AGRIscora is a farm-management dashboard built the way the category ships it, then finished with care: a top bar with the name, the field and four tabs (Field, Plan, Compare, Data), a fixed settings rail on the left, and calm raised panels on the right. It sits on a deep field green at night-office brightness by default, with a light theme for projectors and print. Nothing about the frame is novel on purpose; the craft is in the numbers, the hairlines and the restraint.

Colour carries data and verdicts, not decoration. The neutral layers are all greens of one hue, text is near-white ink, and the primary action is plain full ink rather than a brand hue. The only saturated colours on screen are the six crop colours (the data series), the weather and water colours inside charts, and green or red when a number is better or worse for the farmer. The farmer's own rotation is always in full ink; the scorer's best match is shown neutral beside it, never as a winner colour.

Density is office-desktop comfortable: 16 px body, 13 px floor, tabular numerals everywhere so columns of numbers line up. Depth comes from tonal panels and hairlines; shadows appear only on things that float (popovers). The rejected earlier look (condensed display type, uppercase eyebrows, middle-dot meta lines, monospace numbers) does not return.

**Key Characteristics:**
- Category-standard shell: 60 px top bar, 300 px settings rail, panels on a 20/28 px main gutter.
- One-hue green neutrals, flat panels with 1 px hairlines, 12 px panel corners.
- Full-ink primary action and selection in both themes.
- Crop colours are the only data series; green and red only mean better and worse.
- Public Sans 400/500/600/700 with tabular numerals; drawn line icons from Lucide.
- Non-modal info points next to every metric that needs explaining.

## Colors

A single deep field-green hue for every neutral, near-white ink on top, and saturated colour reserved for crops, weather and verdicts.

### Primary
- **Full Ink** (primary; light theme light-primary): the primary button, the selected tab underline, the slider fill and thumb ring, the selected rotation row border, the "Your rotation" tag and the farmer's own bar and chart point. Light on dark, deep pine green on light. It replaced the planned wheat gold, which collided with corn's data colour.
- **Pine Ink** (light-primary-hover / primary-hover): the pressed-darker or brighter step of the primary on hover.

### Secondary
- **Crop Series** (crop-corn, crop-soybean, crop-winter-wheat, crop-sorghum, crop-sunflower, crop-triticale): one colour per crop, used for year bands, crop chips and toggles, month strips, season chart bands and legends. Triticale is the only cover crop; it is drawn at reduced opacity (0.55 to 0.7) to read as a cover, never as a main crop. Labels sitting on crop fills use Band Ink (band-label-ink) in both themes.

### Tertiary
- **Weather and Water** (water, rain, heat, cold, nitro, plus the translucent "water the crop uses" wash): chart-only series in the month-by-month and data views. Water blue doubles as the focus ring and text-selection tint.
- **Verdict Green / Verdict Red** (good, bad): a number that is better or worse for the farmer than its comparison, the "better" zone in scatter charts, and the Good/Poor words in the priority breakdown. Each has a 10 to 14 percent wash for backgrounds.
- **Caution Amber** (warn): rule warnings (same crop twice, pest carry-over), the not-updated banner and the "assumption" source tag.

### Neutral
- **Field Ground** (field-ground): page background and the inverse text on ink fills.
- **Field Panel** (field-panel): panels, top bar, popovers, selected segmented and toggle states.
- **Raised Field** (field-raise): hover fill, group header rows in the comparison table, selected rotation row, drop target.
- **Sunk Field** (field-sunk): settings rail, year cards, selects, rotation rows, segmented tracks, the farmer's column in the comparison table.
- **Hairline** and **Strong Hairline** (hairline, hairline-strong): 1 px dividers, panel and card borders; the strong step for control borders, axes and empty bar tracks.
- **Ink 2** and **Ink 3** (ink-2, ink-3): secondary text (units, sub-lines, legends) and tertiary marks (best-match bar, grip handles, info icons, month initials).

### Named Rules
**The Verdict-Only Rule.** Green and red mean better and worse for this farmer, and nothing else. Every coloured delta also carries an arrow and words ("6.3 in less"); an equal value is ink-2 with an equals sign.

**The Gold Belongs to Corn Rule.** Crop colours are the only data series and are never borrowed for actions, selection or emphasis. The primary is full ink; selection is an ink border or an ink underline.

**The Neutral Best Match Rule.** The scorer's best match is drawn in ink-3 grey beside the farmer's ink bar. It is a reference, not a winner; only the delta under it may turn green or red.

## Typography

**Display Font:** Public Sans (with system-ui, sans-serif)
**Body Font:** Public Sans
**Label/Mono Font:** none; numbers use Public Sans with tabular numerals

**Character:** One plain, public-sector grotesque in four weights. Hierarchy comes from size and weight, never from case, tracking or a second family.

### Hierarchy
- **Display** (600, 32px, 1.1, -0.02em): the four headline numbers and the rank on the Plan tab, entering with a short rise.
- **Brand** (700, 18px, -0.01em): the AGRIscora wordmark in the top bar only.
- **Headline** (600, 18px, 1.3): panel titles.
- **Title** (600, 15px, 1.3): tabs, buttons, sidebar group names, slider labels, rotation names, KPI labels at 14px in ink-2.
- **Body** (400, 16px, 1.5): running text; long explanations capped near 72ch.
- **Body Small** (400, 14px, 1.5): panel sub-lines, popover text, table text, facts lists.
- **Label** (400 or 600, 13px, 1.4): units, legends, axis text, table headers, tags, slider help. 13 px is the floor.

### Named Rules
**The 13 Pixel Floor Rule.** No text renders below 13 px, including chart axes, legends and map labels.

**The Sentence Case Rule.** Labels, headers and tags are sentence case at normal tracking. No uppercase eyebrows, no kickers above headings, no monospace numerals.

**The Tabular Rule.** `font-variant-numeric: tabular-nums` is set on the body and inherited everywhere, so every column of numbers aligns.

## Layout

A fixed app shell: a sticky 60 px top bar spans both columns; below it a 300 px settings rail (sticky, own scroll, sunk background, 20 px padding, 24 px between groups) and a fluid main column (20 px top, 28 px sides, 48 px bottom). Panels stack in the main column with 14 to 16 px gaps. Inside panels, headers wrap title, info point and a right-aligned action; the sub-line drops to its own row.

The Plan tab uses a five-track builder (year, gap, year, gap, year), a five-column result grid divided by vertical hairlines (four metrics and a wider rank column), and rotation rows with a name, a month strip and four number columns. Compare uses a fixed-layout table; Data uses a 1.6:1 two-column split.

Responsive steps: at 1280 px the result grid becomes 2 by 2 with the rank below and the field name leaves the top bar; at 960 px the shell becomes one column, the tabs move to a scrollable 44 px row and the rail turns into an auto-fit grid above the content; at 600 px metric grids go to one or two columns and crop names leave the month strips. Built for the office desktop, working on a phone.

Spacing rhythm is a 4 px base used at 4, 6, 8, 10, 12, 14, 16, 20 and 24 px; panel padding is 18 by 22 px.

## Elevation & Depth

Flat and tonal. Ground, sunk, panel and raise are four steps of the same green, separated by 1 px hairlines; nothing at rest casts a shadow. Only floating layers are lifted: the info popover uses the theme shadow, and the selected segment gets a 1 px contact shadow.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 10px 30px rgb(0 0 0 / .35), 0 2px 6px rgb(0 0 0 / .25)` dark; `0 10px 30px rgb(19 37 26 / .14), 0 2px 6px rgb(19 37 26 / .08)` light): info popovers.
- **Contact** (`box-shadow: 0 1px 3px rgb(0 0 0 / .25)`): the selected button of a segmented control.

### Named Rules
**The Flat Panel Rule.** Panels, cards and rows are separated by tone and hairline, never by shadow. A shadow means the layer floats above the page.

## Shapes

Softly rounded rectangles with a clear scale: 3 px for colour swatches, 6 px for segment buttons, tooltips and month strips, 8 px for buttons, inputs and toggles, 10 px for year cards, rotation rows, popovers and banners, 12 px for panels. Pills (999 px) are reserved for crop chips and small tags. The only circles are slider thumbs, switch knobs and info buttons. Borders are 1 px; a dashed border marks an optional slot (the cover-crop gap) and bare soil is a fine 135 degree hatch.

## Components

### Buttons
Plain and confident, with no lift on hover.
- **Shape:** gently rounded (8px), 38 px tall, 15 px semibold, 8 px icon gap.
- **Primary:** full ink fill with ground-coloured text; used for the one decisive action in a context ("Use this rotation").
- **Hover / Focus:** background steps to primary-hover (secondary steps to raise) over 150 ms; focus is a 2 px water-blue outline offset 2 px.
- **Secondary:** panel fill, strong hairline border, ink text. **Ghost:** transparent until hover. **Small:** 32 px tall, 14 px text.
- **Icon button:** 36 px square, ink-2 icon, raise fill on hover; chevrons rotate 180 degrees when expanded.

### Chips
- **Crop chip:** pill, 32 px, strong hairline border, 10 px crop swatch before the name; draggable onto a year.
- **Tags:** 22 px pills at 13 px semibold. "Your rotation" is solid ink with ground text; pick tags ("Best match", "Option 2") are outlined in ink-2. Source tags (measured, modeled, rule, assumption) are outlined in their own colour.

### Cards / Containers
- **Corner Style:** 12px panels; 10px year cards and rotation rows.
- **Background:** panels on field-panel; year cards and rotation rows on field-sunk; selected row on field-raise with an ink border.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1 px hairline.
- **Internal Padding:** 18 by 22 px panels; 12 to 14 px cards.
- **Year card:** a 6 px crop-colour band across the top edge, the year number, a select, move arrows and a drag grip.

### Inputs / Fields
- **Select:** 40 px, sunk fill, strong hairline border, 8 px corners, semibold value; border lifts to ink-3 on hover.
- **Weight slider:** 6 px track filled in ink up to the value, 20 px panel-coloured thumb with a 3 px ink ring; label left, word value ("Moderate") right, one help line below.
- **Crop toggle:** full-width 38 px row with swatch, name and tick; off is ink-2 with a 45 percent swatch, on is ink on panel with a full swatch.
- **Segmented control:** sunk track, 3 px inset, selected segment on panel with the contact shadow.
- **Focus:** a 2 px water-blue outline, offset 2 px, on every focusable element.

### Navigation
Four text tabs in the top bar at 15 px semibold. Default ink-2, hover and selected ink; the selected tab carries a 3 px ink underline with rounded top corners, inset 12 px. ARIA tabs with arrow, Home and End keys. Below 960 px the tabs wrap to their own scrollable row.

### Info Point
A 24 px round button with a Lucide info icon in ink-3 next to a metric or heading. It opens a 320 px non-modal popover (panel fill, strong hairline, 10 px corners, float shadow, 150 ms rise-in) with a bold title, a close button and short body text. The page stays usable; a click outside, Escape, scroll or resize closes it.

### Delta
A semibold 14 px (13 px in dense cells) line with an arrow icon and words: verdict green when better, verdict red when worse, ink-2 with an equals sign when the same. Direction words are always spelled out.

### Month Strip and Season Chart
The rotation drawn as a horizontal strip of crop-coloured runs (30 px, or 14 px compact), cover crops at 70 percent, bare months as the hatch. The season chart repeats the bands above monthly bars for water, nitrogen or stress, with dashed grid lines, 13 px axis text and an inline legend.

## Do's and Don'ts

### Do:
- **Do** use full ink (primary) for the main action, the selected tab, slider fill and the farmer's own rotation.
- **Do** give every crop its colour from the crop series and use those colours only for crops.
- **Do** pair every green or red value with an arrow and words such as "less" or "more".
- **Do** show the scorer's best match in neutral ink-3 next to the farmer's ink value.
- **Do** separate layers with the four green tones and 1 px hairlines, keeping panels flat.
- **Do** keep all text at 13 px or larger and in sentence case, with tabular numerals.
- **Do** explain a metric with a non-modal info point rather than a modal or a long caption.
- **Do** define every colour for both themes; dark is the default.

### Don't:
- **Don't** use a crop colour (corn gold especially) for buttons, selection or emphasis.
- **Don't** use green or red for anything except better and worse.
- **Don't** colour the best match as a winner.
- **Don't** bring back the rejected Mockup v2 look: condensed display type, uppercase eyebrows or kickers, middle-dot meta lines, monospace numbers.
- **Don't** put shadows on panels or cards at rest.
- **Don't** offer any cover crop other than triticale.
