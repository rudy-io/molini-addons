import type { Hass } from '../hass/types';
import { numState, fmtKwh } from '../hass/read';

export function MeterCard({ hass }: { hass: Hass }) {
  const hc = numState(hass, 'sensor.molini_index_hc');
  const hp = numState(hass, 'sensor.molini_index_hp');
  return (
    <div class="rounded-xl bg-moli-surface border border-moli-border px-4">
      <Row label="Index heures creuses" value={fmtKwh(hc)} unit="kWh" border />
      <Row label="Index heures pleines" value={fmtKwh(hp)} unit="kWh" />
    </div>
  );
}

function Row({
  label,
  value,
  unit,
  border,
}: {
  label: string;
  value: string;
  unit: string;
  border?: boolean;
}) {
  return (
    <div
      class={`flex items-center justify-between py-2.5 ${border ? 'border-b border-moli-border' : ''}`}
    >
      <span class="text-sm text-moli-muted">{label}</span>
      <span class="text-[15px] font-medium">
        {value} {unit}
      </span>
    </div>
  );
}
