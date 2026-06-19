import { fmtW } from '../hass/read';

// Dessin d'un panneau solaire qui « se remplit » par le bas selon sa production.
export function PanelModule({
  id,
  name,
  watts,
  max,
}: {
  id: string;
  name: string;
  watts: number | null;
  max: number;
}) {
  const pct = watts == null ? 0 : Math.max(0, Math.min(1, watts / max));
  const low = watts != null && pct > 0 && pct < 0.2;
  const fillH = 56 * pct; // hauteur remplie dans la zone y∈[4,60]
  const clip = `pm-${id}`;

  return (
    <div data-panel-tile class="flex flex-col items-center rounded-lg bg-moli-surface2 p-2">
      <svg viewBox="0 0 100 64" class="w-full">
        <clipPath id={clip}>
          <rect x="6" y="4" width="88" height="56" rx="3" />
        </clipPath>
        {/* cellules éteintes */}
        <rect x="6" y="4" width="88" height="56" rx="3" fill="#0e1b2a" />
        {/* remplissage production (par le bas) */}
        <rect
          x="6"
          y={60 - fillH}
          width="88"
          height={fillH}
          fill={low ? '#ba7517' : '#1d9e75'}
          fill-opacity="0.62"
          clip-path={`url(#${clip})`}
        />
        {/* grille de cellules */}
        <g stroke="#243044" stroke-width="1.3">
          <line x1="28" y1="4" x2="28" y2="60" />
          <line x1="50" y1="4" x2="50" y2="60" />
          <line x1="72" y1="4" x2="72" y2="60" />
          <line x1="6" y1="32" x2="94" y2="32" />
        </g>
        {/* cadre */}
        <rect x="6" y="4" width="88" height="56" rx="3" fill="none" stroke="#3a4456" stroke-width="1.5" />
      </svg>
      <div class="mt-1 text-[12px] text-moli-muted">{name}</div>
      <div class="text-[14px] font-medium leading-tight">
        {fmtW(watts)}
        <span class="text-[10px] text-moli-muted"> W</span>
      </div>
    </div>
  );
}
