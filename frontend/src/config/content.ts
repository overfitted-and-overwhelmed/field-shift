/** Page text. Edit here, no component changes needed. */
export const CONTENT = {
  brand: 'Field Shift',
  brandSub: 'Explorer',
  nav: [
    { id: 'inputs', label: 'Your situation' },
    { id: 'field', label: 'Your field' },
    { id: 'build', label: 'Build your rotation' },
    { id: 'compare', label: 'Compare' },
    { id: 'season', label: 'Season view' },
    { id: 'why', label: 'Why & what to check' },
  ],
  title: 'Try your own rotation against the best alternatives',
  lead: 'Set what matters to you, then change your rotation: drag crops, swap them, add a cover crop. Every number on this page is recalculated from 35 seasons of NASA POWER weather for your field.',
  inputs: { eyebrow: 'Step 1 · What the scorer should know', title: 'Your situation and priorities' },
  field: { eyebrow: 'Your field', title: 'Where the data comes from', lead: 'The fields around your farm from the USDA Cropland Data Layer and Sentinel-2 NDVI. The map is for orientation: the numbers below are computed for the field in Kearny County, Kansas.' },
  build: {
    eyebrow: 'Step 2 · Build your rotation', title: 'Your rotation, year by year',
    lead: 'Drag a crop from the shelf onto a year to replace it, drag years to reorder them, or use the menus and arrows. Choose for each year whether a triticale cover crop follows the harvest. The scorer compares three-crop rotations, so yours has three crops too. It starts from your field’s crop history (USDA CDL).',
  },
  compare: {
    eyebrow: 'Step 3 · Side by side', title: 'Your rotation against the scorer’s picks',
    lead: 'The picks come from the scorer for your crops and priorities; they do not change while you edit your rotation. Green and red compare each pick with your rotation. Tags show how each number is made.',
  },
  season: {
    eyebrow: 'Step 4 · Month by month', title: 'What is on the field, and what it needs',
    lead: 'A typical year from 35 years of NASA POWER weather, not a forecast. The nitrogen view shows fertilizer per season by K-State rules; there is no monthly soil nitrate balance because no source gives loss rates.',
  },
  why: { eyebrow: 'Step 5 · Reasons, evidence and open questions' },
  caution: {
    title: 'This tool supports your judgment. It does not replace it.',
    text: 'The model uses regional weather, generic crop coefficients, K-State nitrogen rules and county yields. Before changing a rotation, check the open questions with your K-State Research and Extension agronomist, your NRCS office and your groundwater district (GMD 3).',
  },
  credits: 'Field Shift Explorer, NASA Space Apps 2026. Full irrigation on every season is an assumption until you can set it for your farm.',
};
