import { humanize } from './crops';
/** Priority (weight) labels. Ids come from `weights` in the data. */
export const PRIORITY_LABELS: Record<string, string> = { water: 'Save water', profit: 'Profit', soil: 'Soil health', erosion: 'Wind erosion' };
export const priorityLabel = (id: string) => PRIORITY_LABELS[id] ?? humanize(id);
