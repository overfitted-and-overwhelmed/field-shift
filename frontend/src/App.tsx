import { useMemo, useState } from 'react';
import { Detail } from './components/Detail';
import { InputForm } from './components/InputForm';
import { Options } from './components/Options';
import { Tooltip } from './components/Tooltip';
import { CONTENT } from './config/content';
import { cropLabel } from './config/crops';
import { priorityLabel } from './config/priorities';
import { DATA_URL, useExplorerData } from './data/load';
import { activeMetrics } from './data/metrics';
import { goForm, toQuery, useRoute, type FieldRequest, type LatLon } from './lib/request';
import type { Units } from './lib/units';
import type { ExplorerData } from './types';

export default function App() {
  const route = useRoute();
  if (route.page === 'form') return <InputForm key={route.prefill ? toQuery(route.prefill) : ''} prefill={route.prefill} />;
  return <Results key={toQuery(route.req)} req={route.req} />;
}

type ResultsRequest = FieldRequest & { location: LatLon };

function Results({ req }: { req: ResultsRequest }) {
  const state = useExplorerData(req);
  if (state.status === 'loading') return <main className="page"><p role="status" className="note">Loading…</p></main>;
  if (state.status === 'error')
    return (
      <main className="page">
        <p role="alert" className="note"><b>The data could not be loaded.</b> {state.error} <code>{DATA_URL}</code></p>
      </main>
    );
  return <Explorer data={state.data} req={req} />;
}

function Explorer({ data, req }: { data: ExplorerData; req: ResultsRequest }) {
  const [selectedId, setSelectedId] = useState(data.options[0]?.id ?? data.current.id);
  const [units, setUnits] = useState<Units>('in');
  const metrics = useMemo(() => activeMetrics(data), [data]);
  const mctx = { units, nRotations: data.nRotations };
  const selected = data.rotations.find((r) => r.id === selectedId) ?? data.current;
  const f = data.field;
  const placeholder = data.rotations.some((r) => r.placeholder);

  return (
    <>
      <header className="top"><div className="page head-row"><span className="brand">{CONTENT.brand}</span><button type="button" className="link" onClick={() => goForm(req)}>← Change inputs</button></div></header>
      <main className="page">
        <div className="intro">
          <p className="where">{f.name}, from {f.rotation_start_year}</p>
          <h1>{CONTENT.title}</h1>
          <p className="lead">{CONTENT.lead}</p>
          <dl className="facts">
            <div><dt>Location</dt><dd>{req.location.lat.toFixed(4)}, {req.location.lon.toFixed(4)}{f.lat.toFixed(2) !== req.location.lat.toFixed(2) || f.lon.toFixed(2) !== req.location.lon.toFixed(2) ? ` (data so far only for ${f.name}, ${f.lat.toFixed(4)}, ${f.lon.toFixed(4)})` : ''}</dd></div>
            <div><dt>Field</dt><dd>{f.soil.texture}, {f.elevation_ft.toLocaleString('en-US')} ft, grown last: {cropLabel(f.previous_crop).toLowerCase()}</dd></div>
            <div><dt>Crops</dt><dd>{req.crops.map(cropLabel).join(', ')}</dd></div>
            <div><dt>Weighted for</dt><dd>{data.priorities.map((p) => `${priorityLabel(p.id).toLowerCase()} ${p.weight}/5`).join(', ')}</dd></div>
            {placeholder && <div><dt>Note</dt><dd>Some values are still placeholders.</dd></div>}
          </dl>
        </div>
        <Options data={data} metrics={metrics} mctx={mctx} selectedId={selectedId} onSelect={setSelectedId} units={units} onUnits={setUnits} />
        <Detail data={data} r={selected} metrics={metrics} mctx={mctx} units={units} />
      </main>
      <footer className="foot"><div className="page"><p>{CONTENT.footer}</p></div></footer>
      <Tooltip />
    </>
  );
}
