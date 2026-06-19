import type { Hass } from '../hass/types';
import { Gauge } from './Gauge';
import { numState, fmtKwh } from '../hass/read';

export function ProductionHero({ hass }: { hass: Hass }) {
  const prod = numState(hass, 'sensor.molini_solaire_production');
  const conso = numState(hass, 'sensor.molini_consommation_maison');
  const today = numState(hass, 'sensor.molini_solaire_production_aujourd_hui');

  return (
    <div class="space-y-3">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Gauge value={prod} max={5000} label="Production solaire" color="#1d9e75" />
        <Gauge
          value={conso}
          max={6000}
          label="Consommation maison"
          color="#378add"
          mutedLabel="non suivie"
        />
      </div>
      <div class="rounded-lg bg-moli-surface border border-moli-border px-4 py-3 flex items-baseline justify-between">
        <span class="text-sm text-moli-muted">Produit aujourd'hui</span>
        <span class="text-xl font-medium">
          {fmtKwh(today)}
          <span class="text-xs text-moli-muted"> kWh</span>
        </span>
      </div>
    </div>
  );
}
