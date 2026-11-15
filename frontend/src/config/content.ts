import type { Tab } from '../lib/request';

/** Page text. Short, in the farmer's words. Edit here, no component changes needed. */
export const CONTENT = {
  brand: 'AGRIscora',
  tabs: [
    { id: 'field', label: 'Field' },
    { id: 'plan', label: 'Plan' },
    { id: 'compare', label: 'Compare' },
    { id: 'data', label: 'Data' },
  ] as { id: Tab; label: string }[],
  plan: {
    builder: 'Your rotation',
    builderHint: 'Drag a crop onto a year or pick it from the list. Between two years you can add a cover crop.',
    sclerotinia: 'Sunflower and soybean both carry white mold (Sclerotinia), which survives years in the soil. Grow one of them at most once in three years; this rotation is ranked after all that do.',
    result: 'What your rotation means for your field',
    rotations: 'Your rotation and the best suggestions',
    rotationsHint: 'Choose a rotation to see it month by month. The suggestions come from the scorer for your priorities and crops.',
  },
  compare: { title: 'Compare rotations', chart: 'Water against fertilizer', strengths: 'Strengths by priority' },
  field: { title: 'Your field and its neighbours', hint: 'USDA crop map and Sentinel-2 crop vigour (NDVI). Zoom and click fields to look around; the numbers in the other tabs are computed for your field in Kearny County, Kansas.' },
  data: { title: 'Where the numbers come from', weather: 'The 35 seasons behind every number', metrics: 'What each number means', sources: 'Sources', assumptions: 'Assumptions to check' },
  assumptions: [
    'Every season is irrigated in full; the irrigation level cannot be chosen yet.',
    'Weather is NASA POWER on a ~50 km grid, not a station on your farm.',
    'Yields are county averages from USDA NASS, adjusted for the crop before.',
    'The only cover crop so far is triticale; it is not irrigated.',
    'At most one sunflower or soybean crop in three years (white mold, NDSU). Rotations with more come after all others in the ranking.',
    'Prices and costs are not part of the comparison.',
  ],
  caution: 'Talk to your K-State Research and Extension agronomist, your NRCS office and your groundwater district (GMD 3) before you change a rotation.',
};
