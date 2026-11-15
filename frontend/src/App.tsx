import { useEffect, useMemo, useState } from 'react';
import { ScrollTop } from './components/ScrollTop';
import { Tooltip } from './components/Tooltip';
import { CONTENT } from './config/content';
import { cropLabel } from './config/crops';
import { useExplorerData } from './data/load';
import { activeMetrics } from './data/metrics';
import { apiQuery, noCover, usePageState } from './lib/request';
import type { Units } from './lib/units';
import { Builder } from './sections/Builder';
import { Compare } from './sections/Compare';
import { FieldMap } from './sections/FieldMap';
import { Season } from './sections/Season';
import { Situation } from './sections/Situation';
import { Why } from './sections/Why';

/**
 * One long page: inputs → map → rotation builder → comparison → season view → reasons.
 * Every input change reloads the data from the explorer API; the last good data stays on screen meanwhile.
 */
export default function App() {
  const [state, set] = usePageState();
  const weights = useMemo(() => state.weights, [state.weights]);
  const { data: raw, loading, error } = useExplorerData(apiQuery(state), weights);
  const [units, setUnits] = useState<Units>('in');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // A built rotation the scorer cannot score: drop the cover crop if no gap fits one, else go back to the crop history.
  // Otherwise a shared link with such a rotation would leave the page without data and without a way to fix it.
  useEffect(() => {
    if (!error || !state.rotation) return;
    const name = state.rotation.map(cropLabel).join(' → ');
    if (state.cover.some(Boolean) && error.includes('cover crop')) {
      const after = /fits after (.*)\)/.exec(error)?.[1]?.split(', ').map(cropLabel).join(', ');
      setNotice(`A triticale cover crop does not fit${after ? ` after ${after}` : ''} in ${name} (the gap is too short), so it is scored without one.`);
      set((s) => ({ ...s, cover: noCover() }));
    } else if (error.includes('not scored') && !error.includes('cover crop')) { // a cover-crop error here is stale (cover already dropped)
      setNotice(`The scorer has no result for ${name}; showing your crop-history rotation.`);
      set((s) => ({ ...s, rotation: null, cover: noCover() }));
    }
  }, [error, state.rotation, state.cover, set]);

  const data = raw;
  const metrics = useMemo(() => (data ? activeMetrics(data) : []), [data]);
  const mctx = { units, nRotations: data?.nRotations ?? null };
  const selected = data ? data.rotations.find((r) => r.id === selectedId) ?? data.options[0] ?? data.current : null;
  const edited = state.rotation != null;

  // the page title tells where the data is for
  useEffect(() => { document.title = data ? `${CONTENT.brand} ${CONTENT.brandSub} · ${data.field.name}` : `${CONTENT.brand} ${CONTENT.brandSub}`; }, [data]);

  const view = (id: string) => {
    setSelectedId(id);
    document.getElementById('season')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  };

  return (
    <div className="wrap">
      <header className="top">
        <div className="brand">{CONTENT.brand} <span>{CONTENT.brandSub}</span></div>
        <nav className="nav" aria-label="Sections">{CONTENT.nav.map((n) => <a key={n.id} href={`#${n.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(n.id)?.scrollIntoView({ behavior: 'smooth' }); }}>{n.label}</a>)}</nav>
        {/* status only while loading or after an error; nothing when the data is up to date */}
        <span className={`flag${error ? ' err' : ' busy'}`} role="status" hidden={!error && !loading}>{error ? 'Data could not be updated' : 'Updating…'}</span>
      </header>

      <div className="hero">
        <p className="eyebrow">{data ? `${data.field.name} · rotation from ${data.field.rotation_start_year}` : 'Field Shift'}</p>
        <h1>{CONTENT.title}</h1>
        <p className="lead">{CONTENT.lead}</p>
      </div>

      {error && !data && !notice && <p role="alert" className="note warn"><b>The data could not be loaded.</b> {error}</p>}
      {error && data && !state.rotation && !notice && <p role="alert" className="note warn">{error}</p>}

      <Situation state={state} set={set} />
      <FieldMap />
      <Builder state={state} set={(f) => { setNotice(null); set(f); }} data={data} error={error} loading={loading} notice={notice} />

      {data && selected ? (
        <div className={`results${loading ? ' stale' : ''}`} aria-busy={loading}>
          <Compare data={data} metrics={metrics} mctx={mctx} edited={edited} units={units} onUnits={setUnits} onView={view} />
          <Season data={data} selected={selected} onSelect={setSelectedId} units={units} />
          <Why data={data} selected={selected} metrics={metrics} mctx={mctx} units={units} />
        </div>
      ) : !error && <p className="note" role="status">Loading the scorer’s rotations…</p>}

      <footer>
        <span>Data: {data ? Object.values(data.sources).map((s) => s.title).join(' · ') : 'NASA POWER · USDA NASS · USDA NRCS SSURGO · K-State MF2586'}</span>
        <span>{CONTENT.credits}</span>
      </footer>
      <ScrollTop />
      <Tooltip />
    </div>
  );
}
