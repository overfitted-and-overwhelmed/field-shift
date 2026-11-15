import { humanize } from './crops';
/** Priority (weight) labels. The ids are the scorer's criteria (score_parts) and are sent to the API as weights. */
export const PRIORITY_LABELS: Record<string, string> = { water: 'Save water', risk: 'Low weather risk', soil_health: 'Soil health', nitrogen: 'Less fertilizer', overall: 'Overall' };
/** Priorities the farmer can weight on the form. */
export const PRIORITY_IDS = ['water', 'risk', 'soil_health', 'nitrogen'];
export const priorityLabel = (id: string) => PRIORITY_LABELS[id] ?? humanize(id);
