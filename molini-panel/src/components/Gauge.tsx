import { fmtW } from '../hass/read';

// Jauge demi-cercle (arc du haut), remplie de gauche (0) à droite (max).
export function Gauge({
  value,
  max,
  label,
  unit = 'W',
  color,
  mutedLabel = 'non suivie',
}: {
  value: number | null;
  max: number;
  label: string;
  unit?: string;
  color: string;
  mutedLabel?: string;
}) {
  const available = value != null;
  const v = value ?? 0;
  const pct = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
  const R = 80;
  const CX = 100;
  const CY = 100;
  const arcLen = Math.PI * R;
  // Arc du haut : de (20,100) à (180,100), sweep=1 (sens horaire écran → bombé vers le haut).
  const track = `M${CX - R},${CY} A${R},${R} 0 0 1 ${CX + R},${CY}`;

  return (
    <div class="rounded-xl bg-moli-surface border border-moli-border p-4">
      <div class="text-sm text-moli-muted mb-1">{label}</div>
      <svg viewBox="0 0 200 116" class="block w-full max-w-[260px] mx-auto">
        <path d={track} fill="none" stroke="#2a313d" stroke-width="13" stroke-linecap="round" />
        {available && (
          <path
            d={track}
            fill="none"
            stroke={color}
            stroke-width="13"
            stroke-linecap="round"
            stroke-dasharray={arcLen}
            stroke-dashoffset={arcLen * (1 - pct)}
          />
        )}
        <text
          x="100"
          y="93"
          text-anchor="middle"
          style={{ fill: '#e6e9ef', fontSize: '30px', fontWeight: 500 }}
        >
          {available ? fmtW(value) : '—'}
        </text>
        <text x="100" y="110" text-anchor="middle" style={{ fill: '#9aa3b2', fontSize: '12px' }}>
          {available ? unit : mutedLabel}
        </text>
      </svg>
    </div>
  );
}
