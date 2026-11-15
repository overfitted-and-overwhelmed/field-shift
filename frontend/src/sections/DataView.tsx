import { ChevronDown, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import { CONTENT } from '../config/content';
import { cropColor, cropLabel } from '../config/crops';
import { TAG_HELP, TAG_LABELS, type MetricCtx, type MetricDef, type Tag } from '../config/metrics';
import { priorityLabel } from '../config/priorities';
import { fmtWater, inToUnit, type Units } from '../lib/units';
import type { ExplorerData } from '../types';

/** Plain names for the API's provenance keys (which field of explorer.json a source feeds). */
const PROV_LABELS: Record<string, string> = {
  'climate.rain_in': 'rain per year', 'climate.deficit_apr_sep_in': 'water missing April to September', 'climate.et0_apr_sep_in': 'reference water use',
  'climate.heat_days_ge_35': 'hot days', 'field.crop_history': 'crop history', 'field.elevation_ft': 'elevation', 'field.previous_crop': 'last crop',
  'field.rotation_start_year': 'start year', 'field.slope_pct': 'slope', 'field.soil': 'soil', 'monthly.cold_stress_years_pct': 'cold stress',
  'monthly.et_in': 'crop water use', 'monthly.heat_years_pct': 'heat stress', 'monthly.irr_in': 'irrigation by month', 'monthly.kill_years_pct': 'killing frost',
  'monthly.heat_days': 'heat stress days', 'monthly.cold_stress_days': 'cold stress days', 'monthly.kill_days': 'killing frost days',
  'monthly.kind': 'what is on the field', 'monthly.rain_in': 'rain by month', 'rotations.*': 'scores and ranking', 'sequence.harvest_date': 'harvest dates',
  'sequence.irr_in': 'irrigation per season', 'sequence.irrigation': 'irrigation level', 'sequence.n_adj_lb': 'nitrogen credit', 'sequence.n_lb': 'nitrogen fertilizer',
  'sequence.plant_date': 'planting dates', 'sequence.yield': 'yield', 'sequence.yield_pct_rotation': 'yield effect of the crop before', 'summary.bare_months': 'bare soil',
};
/** The scorer's sources are titled with the repository name; the product is AGRIscora. */
const sourceTitle = (t: string) => t.replace(/^Field Shift\b/, 'AGRIscora');
const provLabel = (k: string) => PROV_LABELS[k] ?? k.split('.').pop()!.replace(/_/g, ' ');
/** Sources the API cites in season notes rather than in its provenance table. */
const SOURCE_USE: Record<string, string> = {
  seifert_2017: 'yield drop when corn or soybean follows itself',
  ndsu_sunflower: 'white mold (Sclerotinia): at most one sunflower or soybean crop in three years',
  sare_2007: 'extra nitrogen after a cover crop',
};

type Series = 'rain' | 'deficit' | 'heat';
const SERIES: Record<Series, { label: string; unit: (u: Units) => string; help: string }> = {
  rain: { label: 'Rain per year', unit: (u) => u, help: 'Total precipitation of the calendar year at your field (NASA POWER).' },
  deficit: { label: 'Water missing, April to September', unit: (u) => u, help: 'Reference crop water use (ET0) minus rain in the growing months: what irrigation has to make up.' },
  heat: { label: 'Days at 35 °C or hotter', unit: () => 'days', help: 'Days with a maximum temperature of 35 °C (95 °F) or more.' },
};

/** The 35 weather years every number is computed from, one bar per year, with the average as a line. */
function Weather({ data, units }: { data: ExplorerData; units: Units }) {
  const [series, setSeries] = useState<Series>('rain');
  const c = data.climate;
  const raw = series === 'rain' ? c.rain_in : series === 'deficit' ? c.deficit_apr_sep_in : c.heat_days_ge_35;
  const vals = series === 'heat' ? raw : raw.map((v) => inToUnit(v, units));
  const unit = SERIES[series].unit(units);
  const fmt = (v: number) => (series === 'heat' ? `${Math.round(v)} days` : units === 'in' ? `${v.toFixed(1)} in` : `${Math.round(v)} mm`);
  const n = vals.length, w = 1000, h = 240, L = 60, R = 86, T = 12, B = 30, bw = (w - L - R) / n;
  const top = Math.max(...vals) || 1, mean = vals.reduce((a, b) => a + b, 0) / n;
  const stepBase = 10 ** Math.floor(Math.log10(top / 3));
  const step = [1, 2, 2.5, 5, 10].map((k) => k * stepBase).find((k) => top / k <= 4) ?? stepBase * 10;
  const max = Math.ceil((top * 1.04) / step) * step;
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  const y = (v: number) => T + (h - T - B) - (v / max) * (h - T - B);
  const lo = vals.indexOf(Math.min(...vals)), hi = vals.indexOf(Math.max(...vals));
  return (
    <section className="panel weather" aria-labelledby="weather-h">
      <header className="panel-head">
        <h2 id="weather-h">{CONTENT.data.weather}</h2>
        <p className="panel-sub">{SERIES[series].help}</p>
      </header>
      <div className="toolbar">
        <div className="seg" role="group" aria-label="Weather measure">
          {(Object.keys(SERIES) as Series[]).map((s) => <button key={s} type="button" aria-pressed={series === s} onClick={() => setSeries(s)}>{SERIES[s].label}</button>)}
        </div>
        <p className="weather-facts">
          <span>Average <b>{fmt(mean)}</b></span>
          <span>Lowest <b>{fmt(vals[lo])}</b> in {c.weather_years[lo]}</span>
          <span>Highest <b>{fmt(vals[hi])}</b> in {c.weather_years[hi]}</span>
        </p>
      </div>
      <div className="chart-scroll">
        <svg viewBox={`0 0 ${w} ${h}`} className="chart" role="img" aria-label={`${SERIES[series].label}, ${c.weather_years[0]} to ${c.weather_years[n - 1]}`} style={{ minWidth: 720 }}>
          {ticks.map((v) => <g key={v}><line className="grid" x1={L} x2={w - R} y1={y(v)} y2={y(v)} /><text x={L - 8} y={y(v) + 4} textAnchor="end">{+v.toFixed(1)} {unit}</text></g>)}
          {vals.map((v, i) => (
            <g key={c.weather_years[i]}>
              <rect x={L + i * bw + 2} y={y(v)} width={bw - 4} height={y(0) - y(v)} rx={2} className={`b-year ${series}`} />
              <rect x={L + i * bw} y={T} width={bw} height={h - T - B} fill="transparent" data-tip={`${c.weather_years[i]}: ${fmt(v)}`} />
              {(i % 5 === 0 || i === n - 1) && <text x={L + i * bw + bw / 2} y={h - 10} textAnchor="middle">{c.weather_years[i]}</text>}
            </g>
          ))}
          <line x1={L} x2={w - R + 6} y1={y(mean)} y2={y(mean)} className="l-mean" />
          <text x={w - R + 10} y={y(mean) + 4} className="mean-label">average</text>
        </svg>
      </div>
    </section>
  );
}

/** One number explained: what it is, what kind of number, and the sources behind it. */
function MetricRow({ m, data, ctx }: { m: MetricDef; data: ExplorerData; ctx: MetricCtx }) {
  const [open, setOpen] = useState(false);
  const prov = m.provenance.map((k) => data.provenance[k]).filter(Boolean);
  const sources = [...new Set(prov.map((p) => p.source).filter((s): s is string => !!s))].map((k) => ({ key: k, ...data.sources[k] })).filter((s) => s.title);
  const id = `metric-${m.key}`;
  return (
    <li className={`metric${open ? ' open' : ''}`}>
      <button type="button" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        <ChevronDown size={18} className="chev" aria-hidden="true" />
        <span className="metric-name">{m.label}</span>
        <span className="metric-group">{priorityLabel(m.group)}</span>
        <span className={`tag ${m.tag}`} data-tip={TAG_HELP[m.tag]}>{TAG_LABELS[m.tag]}</span>
      </button>
      {open && (
        <div className="metric-more" id={id}>
          <p>{m.info}</p>
          <p className="metric-unit">Unit: {m.unit(ctx)}. {m.better === 'lower' ? 'Lower is better.' : 'Higher is better.'}</p>
          {sources.length > 0 && <ul className="src-list">{sources.map((s) => (
            <li key={s.key}>{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{sourceTitle(s.title)}<ExternalLink size={14} aria-hidden="true" /></a> : sourceTitle(s.title)}</li>
          ))}</ul>}
        </div>
      )}
    </li>
  );
}

/** Data tab: the weather years, every number explained, the assumptions and the sources. */
export function DataView({ data, metrics, ctx, units }: { data: ExplorerData; metrics: MetricDef[]; ctx: MetricCtx; units: Units }) {
  const [tag, setTag] = useState<Tag | 'all'>('all');
  const shown = metrics.filter((m) => tag === 'all' || m.tag === tag);
  const notes = new Set(data.rotations.flatMap((r) => r.sequence.flatMap((s) => s.effects.map((e) => e.source))).filter(Boolean));
  const used = (key: string) => {
    const names = Object.entries(data.provenance).filter(([, p]) => p.source === key).map(([k]) => provLabel(k));
    if (SOURCE_USE[key]) names.push(SOURCE_USE[key]);
    else if (notes.has(key)) names.push('notes on the seasons');
    return [...new Set(names)].join(', ').replace(/^./, (c) => c.toUpperCase());
  };
  const f = data.field;
  return (
    <div className="dataview">
      <Weather data={data} units={units} />
      <div className="data-cols">
        <section className="panel" aria-labelledby="metrics-h">
          <header className="panel-head">
            <h2 id="metrics-h">{CONTENT.data.metrics}</h2>
            <div className="seg" role="group" aria-label="Kind of number">
              {(['all', 'measured', 'modeled', 'rule', 'assumption'] as const).map((t) => (
                <button key={t} type="button" aria-pressed={tag === t} onClick={() => setTag(t)}>{t === 'all' ? 'All' : TAG_LABELS[t]}</button>
              ))}
            </div>
          </header>
          {shown.length ? <ul className="metric-list">{shown.map((m) => <MetricRow key={m.key} m={m} data={data} ctx={ctx} />)}</ul>
            : <p className="empty">No number of this kind on the dashboard. Rotation numbers are modeled or follow a rule; measured data is the weather and the field itself.</p>}
        </section>
        <div className="data-side">
          <section className="panel" aria-labelledby="assume-h">
            <header className="panel-head"><h2 id="assume-h">{CONTENT.data.assumptions}</h2></header>
            <ul className="plain-list">{CONTENT.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            <p className="caution">{CONTENT.caution}</p>
          </section>
          <section className="panel" aria-labelledby="hist-h">
            <header className="panel-head"><h2 id="hist-h">Your field’s history</h2></header>
            <ol className="history" aria-label="Crop per year, USDA Cropland Data Layer">
              {f.crop_history.map((h) => <li key={h.year} style={{ background: cropColor(h.crop) }} data-tip={`${h.year}: ${cropLabel(h.crop)}`} />)}
            </ol>
            <p className="history-ends"><span>{f.crop_history[0]?.year}</span><span>{f.crop_history[f.crop_history.length - 1]?.year}</span></p>
            <dl className="facts">
              <div><dt>Soil</dt><dd>{f.soil.texture}, {f.soil.organic_matter_pct} % organic matter</dd></div>
              <div><dt>Water the soil holds</dt><dd>{fmtWater(f.soil.water_capacity_in, units)}</dd></div>
              <div><dt>Elevation and slope</dt><dd>{f.elevation_ft.toLocaleString('en-US')} ft, {f.slope_pct} % slope</dd></div>
            </dl>
          </section>
        </div>
      </div>
      <section className="panel" aria-labelledby="src-h">
        <header className="panel-head"><h2 id="src-h">{CONTENT.data.sources}</h2></header>
        <table className="data-table sources">
          <thead><tr><th scope="col">Source</th><th scope="col">Numbers based on it</th></tr></thead>
          <tbody>
            {Object.entries(data.sources).map(([key, s]) => (
              <tr key={key}>
                <th scope="row">{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{sourceTitle(s.title)}<ExternalLink size={14} aria-hidden="true" /></a> : sourceTitle(s.title)}</th>
                <td>{used(key) || '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
