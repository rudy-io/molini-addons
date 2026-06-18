import type { Hass } from './hass/types';

export function App({ hass }: { hass: Hass }) {
  // Stub jusqu'à Task 4 (EnergyScreen).
  return (
    <div class="p-6 text-moli-text">Moli — {Object.keys(hass.states).length} entités chargées</div>
  );
}
