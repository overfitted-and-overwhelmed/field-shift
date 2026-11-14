import { useMemo, useState } from 'react';
import { Detail } from './components/Detail';
import { Options } from './components/Options';
import { Tooltip } from './components/Tooltip';
import { CONTENT } from './config/content';
import { priorityLabel } from './config/priorities';
import { DATA_URL, useExplorerData } from './data/load';
import { activeMetrics } from './data/metrics';
import type { Units } from './lib/units';
import type { ExplorerData } from './types';

export default function App() {
  const state = useExplorerData();
  if (state.status === 'loading') return <main className="page"><p role="status" className="note">Loading…</p></main>;
  if (state.status === 'error')
    return (
      <main className="page">
        <p role="alert" className="note"><b>The data could not be loaded.</b> {state.error} <code>{DATA_URL}</code></p>
      </main>
    );
  return <Explorer data={state.data} />;
}

function Explorer({ data }: { data: ExplorerData }) {
  const [selectedId, setSelectedId] = useState(data.options[0]?.id ?? data.current.id);
  const [units, setUnits] = useState<Units>('in');
  const metrics = useMemo(() => activeMetrics(data), [data]);
  const mctx = { units, seasons: data.seasons, capIn: data.cap_in, rotationYears: data.current.sequence.length, prices: data.prices };
  const selected = data.rotations.find((r) => r.id === selectedId) ?? data.current;
  const f = data.field;
  const given = (data.constraints ?? []).filter((c) => c.ok && c.id !== 'start').map((c) => c.label + (c.note && c.id === 'water_right' ? ` (${c.note})` : ''));

  return (
    <>
      <header className="top"><div className="page"><span className="brand">{CONTENT.brand}</span></div></header>
      <main className="page">
        <div className="intro">
          <p className="where">{f.name}{f.start_year ? `, from ${f.start_year}` : ''}</p>
          <h1>{CONTENT.title}</h1>
          <p className="lead">{CONTENT.lead}</p>
          <dl className="facts">
            <div><dt>Weighted for</dt><dd>{data.priorities.map((p) => priorityLabel(p.id).toLowerCase()).join(', ')}</dd></div>
            {given.length > 0 && <div><dt>Given</dt><dd>{given.join(', ')}</dd></div>}
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
