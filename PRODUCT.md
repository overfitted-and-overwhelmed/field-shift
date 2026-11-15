# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: an irrigating farmer in western Kansas (Kearny County, groundwater from the Ogallala aquifer, GMD 3) who wants to try other crop rotations for one field before changing anything. Uses it on a desktop computer in the farm office, with time to experiment. Mobile only has to work, not shine.

Secondary: the NASA Space Apps Challenge 2026 jury, who need to see which NASA and USDA data the numbers rest on.

## Product Purpose

AGRIscora (repository: field-shift) lets the farmer build a crop rotation for their field and see right away what it would mean for irrigation water, nitrogen fertilizer, weather risk and bare soil, compared with the best rotations the scorer found for their priorities. Success: the farmer leaves with a rotation they understand well enough to discuss with their agronomist, and the jury can trace every number to its data.

## Positioning

Every number is computed for this field from 35 seasons of NASA POWER weather (1991–2025), the field's own USDA crop history and K-State nitrogen rules, and it is recomputed live for any rotation the farmer builds, including a cover crop in single gaps. The scorer ranks all 225 three-crop rotations for the farmer's own weights.

## Operating Context

- Workflow: look at the field on the map (start tab); set priorities (water, weather risk, soil health, fertilizer) and allowed crops; build or edit a three-year rotation (drag crops, per-year triticale cover), starting from the field's last three crops; compare it with the scorer's top 3 picks and see any of them month by month; look up where a number comes from.
- There is no separate "today's rotation": the field history is only known for this one field, so it is just where the farmer's own rotation starts. All comparisons are against the farmer's rotation.
- Backend: `uv run python -m explorer.api` (scorer + explorer), frontend `frontend/` (React + Vite) on `/api/explorer`.
- The field map (USDA CDL crops, Sentinel-2 NDVI around the field) is orientation only; it does not change the numbers.

## Capabilities and Constraints

- Rotations have exactly three crops (the scorer ranks three-crop rotations). Crops: corn, soybean, winter wheat, sorghum, sunflower; triticale only as cover crop.
- Data exists for one field (Kearny County, KS) so far.
- Irrigation is assumed full on every season; no prices or profit data.
- Nitrogen is per season (K-State MF2586), not a monthly balance.
- UI language: English.

## Brand Commitments

- Product name: AGRIscora (team decision, 2026-11-15).
- Direction chosen by the team (2026-11-15): the category standard for farm-management dashboards, executed at full craft, modern and lean. No novelty world.
- Tabs: Field (start), Plan, Compare, Data.
- Dark theme by default in a deep, farm-like green; a light theme as a switch (projector, print).
- Written for a farmer who is not technical: plain words, everything important visible or one click away, nothing hidden that matters for the decision.
- The previous look (Mockup v2: condensed display type, uppercase eyebrows, middle-dot meta lines, monospace numbers) was rejected as "too AI-like" and must not return.

## Evidence on Hand

- Live API data: per rotation scores (0 = best of 225), irrigation in/yr with 10th–90th percentile, N lb/acre/yr, bare-soil months, heat/cold stress days, seasons with dates, yields, previous-crop effects, monthly water and stress.
- Sources with titles in the API response (`sources`, `provenance` per field); frontend live sources in `frontend/frontend_sources.md`; backend sources in `data/base-data/*_sources.md`.
- No testimonials, customers, prices or economic claims exist; none may be invented.

## Product Principles

1. The farmer's own rotation is the centre: the farmer plays, the numbers answer.
2. Show what a farmer decides on first; hard data waits one click away, never gone.
3. Every number can be traced to its source and method in the data view.
4. Plain words from the farm, not from the model.

## Accessibility & Inclusion

Readable for older users on an office monitor: comfortable text sizes, strong contrast, no meaning by colour alone, full keyboard use for the rotation builder.
