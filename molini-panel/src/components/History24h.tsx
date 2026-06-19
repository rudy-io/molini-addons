import { useEffect, useState } from 'preact/hooks';
import type { Hass } from '../hass/types';
import { fetchHistory, type Point } from '../hass/history';

const PROD_COLOR = '#1d9e75';
const CONSO_COLOR = '#378add';

export function History24h({ hass }: { hass: Hass }) {
  const [prod, setProd] = useState<Point[]>([]);
  const [conso, setConso] = useState<Point[]>([]);

  useEffect(() => {
    let alive = true;
    fetchHistory(hass, 'sensor.molini_solaire_production', 24, 'solar').then((p) => {
      if (alive) setProd(p);
    });
    fetchHistory(hass, 'sensor.molini_consommation_maison', 24, 'load').then((p) => {
      if (alive) setConso(p);
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const hasConso = conso.length >= 2;
  const hasData = prod.length >= 2 || hasConso;

  return (
    <div class="rounded-xl bg-moli-surface border border-moli-border p-4">
      <div class="mb-2 flex items-center justify-between">
        <div class="text-[13px] text-moli-muted">24 dernières heures</div>
        <div class="flex items-center gap-3 text-[12px] text-moli-muted">
          <Legend color={PROD_COLOR} label="Production" />
          {hasConso && <Legend color={CONSO_COLOR} label="Consommation" />}
        </div>
      </div>
      {!hasData ? (
        <div class="flex h-40 items-center justify-center text-sm text-moli-muted">
          Pas encore de données
        </div>
      ) : (
        <Chart prod={prod} conso={conso} />
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

function Chart({ prod, conso }: { prod: Point[]; conso: Point[] }) {
  const W = 720;
  const H = 160;
  const pad = 4;
  const all = [...prod, ...conso];
  const xs = all.map((p) => p.t);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const maxV = Math.max(100, ...all.map((p) => p.v));
  const x = (t: number) => pad + ((t - minX) / (maxX - minX || 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - (v / maxV) * (H - 2 * pad);
  const line = (pts: Point[]) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
  const area = (pts: Point[]) =>
    pts.length < 2
      ? ''
      : `${line(pts)} L${x(pts[pts.length - 1].t).toFixed(1)},${H - pad} L${x(pts[0].t).toFixed(1)},${H - pad} Z`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      class="h-40 w-full"
      preserveAspectRatio="none"
      role="img"
      aria-label="Production et consommation des dernières 24 heures"
    >
      {prod.length >= 2 && (
        <>
          <path d={area(prod)} fill={PROD_COLOR} fill-opacity="0.15" />
          <path
            d={line(prod)}
            fill="none"
            stroke={PROD_COLOR}
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
        </>
      )}
      {conso.length >= 2 && (
        <>
          <path d={area(conso)} fill={CONSO_COLOR} fill-opacity="0.12" />
          <path
            d={line(conso)}
            fill="none"
            stroke={CONSO_COLOR}
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
        </>
      )}
    </svg>
  );
}
