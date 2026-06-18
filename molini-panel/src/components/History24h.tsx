import { useEffect, useState } from 'preact/hooks';
import type { Hass } from '../hass/types';
import { fetchHistory, type Point } from '../hass/history';

export function History24h({ hass }: { hass: Hass }) {
  const [points, setPoints] = useState<Point[]>([]);

  useEffect(() => {
    let alive = true;
    fetchHistory(hass, 'sensor.molini_solaire_production', 24).then((p) => {
      if (alive) setPoints(p);
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div class="rounded-xl bg-moli-surface border border-moli-border p-4">
      {points.length < 2 ? (
        <div class="h-40 flex items-center justify-center text-moli-muted text-sm">
          Pas encore de données
        </div>
      ) : (
        <Chart points={points} />
      )}
    </div>
  );
}

function Chart({ points }: { points: Point[] }) {
  const W = 720;
  const H = 160;
  const pad = 4;
  const xs = points.map((p) => p.t);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const maxV = Math.max(100, ...points.map((p) => p.v));
  const x = (t: number) => pad + ((t - minX) / (maxX - minX || 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - (v / maxV) * (H - 2 * pad);
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
  const area = `${line} L${x(maxX).toFixed(1)},${(H - pad).toFixed(1)} L${x(minX).toFixed(1)},${(H - pad).toFixed(1)} Z`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      class="w-full h-40"
      preserveAspectRatio="none"
      role="img"
      aria-label="Production solaire des dernières 24 heures"
    >
      <path d={area} fill="#1d9e75" fill-opacity="0.15" />
      <path
        d={line}
        fill="none"
        stroke="#1d9e75"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
        vector-effect="non-scaling-stroke"
      />
    </svg>
  );
}
