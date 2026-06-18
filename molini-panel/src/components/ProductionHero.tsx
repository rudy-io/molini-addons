import type { Hass } from '../hass/types';
import { numState, fmtW, fmtKwh } from '../hass/read';

// Borne haute de la jauge hero (≈ puissance crête install Carole ~5 kW).
const HERO_MAX_W = 5000;

export function ProductionHero({ hass }: { hass: Hass }) {
  const now = numState(hass, 'sensor.molini_solaire_production');
  const today = numState(hass, 'sensor.molini_solaire_production_aujourd_hui');
  const total = numState(hass, 'sensor.molini_solaire_production_totale');
  const pct = now == null ? 0 : Math.min(100, Math.round((now / HERO_MAX_W) * 100));

  return (
    <div class="grid grid-cols-1 sm:grid-cols-[1.4fr_1fr_1fr] gap-3">
      <div class="rounded-xl bg-moli-surface border border-moli-border p-4">
        <div class="text-sm text-moli-muted">Production en ce moment</div>
        <div class="text-3xl font-medium leading-tight">
          {fmtW(now)}
          <span class="text-sm text-moli-muted"> W</span>
        </div>
        <div class="mt-2.5 h-1.5 rounded-full bg-moli-border overflow-hidden">
          <div class="h-full rounded-full bg-solar" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <Stat label="Aujourd'hui" value={fmtKwh(today)} unit="kWh" />
      <Stat label="Depuis l'origine" value={fmtKwh(total)} unit="kWh" />
    </div>
  );
}

function Stat({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div class="rounded-lg bg-moli-surface border border-moli-border p-4">
      <div class="text-sm text-moli-muted">{label}</div>
      <div class="text-2xl font-medium">
        {value}
        <span class="text-xs text-moli-muted"> {unit}</span>
      </div>
    </div>
  );
}
