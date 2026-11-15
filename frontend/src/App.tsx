import { LoaderCircle, Moon, Sprout, Sun, TriangleAlert } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Tooltip } from './components/Tooltip';
import { CONTENT } from './config/content';
import { cropLabel } from './config/crops';
import { METRICS } from './config/metrics';
import { useExplorerData } from './data/load';
import { CROP_IDS, ROTATION_LENGTH, TABS, apiQuery, noCover, usePageState, type Tab } from './lib/request';
import { useTheme } from './lib/theme';
import type { Units } from './lib/units';
import { CompareView } from './sections/CompareView';
import { DataView } from './sections/DataView';
import { FieldView } from './sections/FieldView';
import { PlanView } from './sections/PlanView';
import { Sidebar } from './sections/Sidebar';
import type { Rotation } from './types';

/**
 * Dashboard: top bar with tabs, settings on the left, one tab on the right.
 * Two requests: the base (the rotation from the field history and the scorer's picks) and, once the farmer edits, their rotation.
 * The last good data stays on screen while new data loads.
 */
export default function App() {
  const [state, set] = usePageState();
  const [theme, toggleTheme] = useTheme();
  const [units, setUnits] = useState<Units>('in');
  const [selectedId, setSelectedId] = useState('mine'); // rotation shown month by month on the Plan tab
  const [notice, setNotice] = useState<string | null>(null);
  const weights = useMemo(() => state.weights, [state.weights]);
  const base = useExplorerData(apiQuery({ ...state, rotation: null, cover: noCover() }), weights);
  const plan = useExplorerData(state.rotation ? apiQuery(state) : null, weights);

  // A rotation the scorer cannot score: drop the cover crop if a gap is too short for one, else go back to the field history.
  useEffect(() => {
    const error = plan.error;
    if (!error || !state.rotation) return;
    const name = state.rotation.map(cropLabel).join(', ');
    if (state.cover.some(Boolean) && error.includes('cover crop')) {
      const after = /fits after (.*)\)/.exec(error)?.[1]?.split(', ').map((c) => cropLabel(c).toLowerCase()).join(' and ');
      setNotice(`A cover crop does not fit${after ? ` after ${after}` : ''}: the gap is too short. Shown without it.`);
      set((s) => ({ ...s, cover: noCover() }));
    } else if (error.includes('not scored') && !error.includes('cover crop')) {
      setNotice(`There is no result for ${name}. Showing the rotation from your field history.`);
      set((s) => ({ ...s, rotation: null, cover: noCover() }));
    }
  }, [plan.error, state.rotation, state.cover, set]);

  const data = base.data;
  const fromHistory = data?.current ?? null; // the field's last three crops: where "your rotation" starts
  const history = data ? data.field.crop_history.map((h) => h.crop).filter((c) => CROP_IDS.includes(c)).slice(-ROTATION_LENGTH) : [];
  const edited = state.rotation != null && (state.rotation.join('-') !== history.join('-') || state.cover.some(Boolean));
  const mine: Rotation | null = edited ? plan.data?.current ?? null : fromHistory;
  const picks = data?.options ?? [];
  const ctx = { units, nRotations: data?.nRotations ?? null };
  const loading = base.loading || plan.loading;
  const userSet = (f: Parameters<typeof set>[0]) => { setNotice(null); set(f); };

  const showMonths = (id: string) => { setSelectedId(id); userSet((s) => ({ ...s, tab: 'plan' })); };

  useEffect(() => { document.title = data ? `${CONTENT.brand}: ${data.field.name}` : CONTENT.brand; }, [data]);
  // a pick the farmer had selected can drop out when the weights change; fall back to their own rotation
  const selectable = ['mine', ...picks.map((r) => r.id)];
  const shownId = selectable.includes(selectedId) ? selectedId : 'mine';

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><span className="brand-mark" aria-hidden="true"><Sprout size={20} strokeWidth={2.25} /></span>{CONTENT.brand}</div>
        {data && <span className="place">{data.field.name}, plans from {data.field.rotation_start_year}</span>}
        <Tabs tab={state.tab} onTab={(tab) => userSet((s) => ({ ...s, tab }))} />
        <span className="sync" role="status" aria-live="polite">
          {loading ? <><LoaderCircle size={16} className="spin" aria-hidden="true" />Updating</> : base.error && data ? <><TriangleAlert size={16} aria-hidden="true" />Not updated</> : null}
        </span>
        <button type="button" className="icon-btn theme" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          {theme === 'dark' ? <Sun size={20} aria-hidden="true" /> : <Moon size={20} aria-hidden="true" />}
        </button>
      </header>

      <Sidebar state={state} set={userSet} units={units} onUnits={setUnits} data={data} />

      <main className="main" id="main">
        {base.error && <p role="alert" className="banner"><TriangleAlert size={18} aria-hidden="true" /><span><b>{data ? 'The numbers could not be updated.' : 'The numbers could not be loaded.'}</b> {base.error}</span></p>}
        {state.tab === 'field' ? <FieldView /> : !data || !fromHistory ? (!base.error && <Skeleton />) : (
          <div role="tabpanel" id={`panel-${state.tab}`} aria-labelledby={`tab-${state.tab}`} className={loading ? 'stale' : ''}>
            {state.tab === 'plan' && <PlanView state={state} set={userSet} data={data} mine={mine} picks={picks} history={history} edited={edited}
              scoring={plan.loading} notice={notice} error={plan.error} ctx={ctx} units={units} selectedId={shownId} onSelect={setSelectedId} />}
            {state.tab === 'compare' && (mine ? <CompareView data={data} mine={mine} picks={picks} metrics={METRICS} ctx={ctx} units={units} set={userSet} onMonths={showMonths} /> : <Skeleton />)}
            {state.tab === 'data' && <DataView data={data} metrics={METRICS} ctx={ctx} units={units} />}
          </div>
        )}
      </main>
      <Tooltip />
    </div>
  );
}

/** Tab bar: standard ARIA tabs, arrow keys move between them. */
function Tabs({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, i: number) => {
    const k = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!k && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? TABS.length - 1 : (i + k + TABS.length) % TABS.length;
    onTab(TABS[next]); refs.current[next]?.focus();
  };
  return (
    <nav className="tabs" role="tablist" aria-label="Dashboard">
      {CONTENT.tabs.map((t, i) => (
        <button key={t.id} ref={(el) => { refs.current[i] = el; }} id={`tab-${t.id}`} type="button" role="tab" aria-selected={tab === t.id} aria-controls={`panel-${t.id}`}
          tabIndex={tab === t.id ? 0 : -1} onClick={() => onTab(t.id)} onKeyDown={(e) => onKey(e, i)}>{t.label}</button>
      ))}
    </nav>
  );
}

function Skeleton() {
  return (
    <div className="skeleton-wrap" aria-busy="true" aria-label="Loading the rotations">
      <div className="panel skeleton tall" /><div className="panel skeleton" /><div className="panel skeleton" />
    </div>
  );
}
