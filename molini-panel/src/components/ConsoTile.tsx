import type { Hass } from '../hass/types';
import { numState, fmtW } from '../hass/read';

const EID = 'sensor.molini_consommation_maison';

// Conditionnel : visible seulement si le capteur conso existe ET a une vraie
// valeur (Linky pas encore en TIC standard chez Carole → masqué).
export function ConsoTile({ hass }: { hass: Hass }) {
  const e = hass.states[EID];
  if (!e || e.state === 'unavailable' || e.state === 'unknown') return null;
  return (
    <div class="rounded-xl bg-moli-surface border border-moli-border p-4">
      <div class="text-sm text-moli-muted">Consommation maison</div>
      <div class="text-2xl font-medium">
        {fmtW(numState(hass, EID))}
        <span class="text-xs text-moli-muted"> W</span>
      </div>
    </div>
  );
}
