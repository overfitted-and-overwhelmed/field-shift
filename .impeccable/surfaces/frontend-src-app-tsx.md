---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: []
---

# Surface: AGRIscora dashboard (frontend/src/App.tsx)

Scope: the whole frontend app, one route. Mode: Operate.
Audience and job: an irrigating Kearny County farmer at the office desktop looks at the field, builds a three-crop rotation and sees what it means for water, fertilizer, weather risk and bare soil against the scorer's three picks; the jury traces every number to its data.
Constraints: tabs Field (start) / Plan / Compare / Data; fixed left sidebar with priorities and allowed crops; dark green theme by default plus a light switch; no separate today's rotation; no dropdowns in the Compare table; cover crops named (triticale); no prices; English UI.

## Direction contract

THESIS: A farm-management dashboard built the way the category ships it, at full craft: the farmer's own rotation sits in the centre and answers live; hard data waits one click away. It refuses the long scrolling report and the template look of the rejected mockup.
OWN-WORLD: Deep field green ground (#12231A) with raised panels (#1A3024), hairline green rules, full-ink text, crop colours as the data series, green/red only for better/worse. Primary action and selection in full ink (light on dark, dark green on light): the planned wheat gold collided with corn's data colour (#E8B23A), so gold belongs to corn. Public Sans throughout with tabular numerals; drawn icons from one library.
STORY: The farmer sees the field, sets what matters, edits three years, reads four numbers with the best match beside them, picks a suggestion to see it month by month or uses it with one click, opens a source only when curious.
FIRST VIEWPORT: Top bar with name, field and tabs; sidebar with four weight sliders and crop toggles; Field tab: the map at full height. Plan tab: compact rotation builder, the four numbers as labelled bars (yours, best match) beside the rank, then the list of your rotation and the three picks with the month-by-month chart of the selected one directly below.
FORM: category standard (canon), chosen by the user over the roll; seed: 89de78bc335b265e
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
