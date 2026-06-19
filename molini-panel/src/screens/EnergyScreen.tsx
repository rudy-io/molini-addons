import type { Hass } from '../hass/types';
import { ProductionHero } from '../components/ProductionHero';
import { PanelDetail } from '../components/PanelDetail';
import { MeterCard } from '../components/MeterCard';
import { History24h } from '../components/History24h';

// Pas de titres de section : le contenu (jauges, panneaux, graphe) est induit.
export function EnergyScreen({ hass }: { hass: Hass }) {
  return (
    <div class="min-h-screen bg-moli-bg text-moli-text">
      <div class="mx-auto max-w-5xl px-4 py-6 space-y-5">
        <ProductionHero hass={hass} />
        <PanelDetail hass={hass} />
        <History24h hass={hass} />
        <MeterCard hass={hass} />
      </div>
    </div>
  );
}
