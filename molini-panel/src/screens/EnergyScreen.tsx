import type { Hass } from '../hass/types';
import { ProductionHero } from '../components/ProductionHero';
import { PanelDetail } from '../components/PanelDetail';
import { MeterCard } from '../components/MeterCard';
import { ConsoTile } from '../components/ConsoTile';
import { History24h } from '../components/History24h';

function SectionTitle({ children }: { children: any }) {
  return <h2 class="text-base font-medium mb-3.5">{children}</h2>;
}

export function EnergyScreen({ hass }: { hass: Hass }) {
  return (
    <div class="min-h-screen bg-moli-bg text-moli-text">
      <div class="mx-auto max-w-5xl px-4 py-6 space-y-7">
        <section>
          <SectionTitle>Production solaire</SectionTitle>
          <ProductionHero hass={hass} />
        </section>

        <section>
          <SectionTitle>Production par panneau</SectionTitle>
          <PanelDetail hass={hass} />
        </section>

        <section>
          <SectionTitle>Production des dernières 24 h</SectionTitle>
          <History24h hass={hass} />
        </section>

        <section>
          <SectionTitle>Compteur électrique</SectionTitle>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <MeterCard hass={hass} />
            <ConsoTile hass={hass} />
          </div>
        </section>
      </div>
    </div>
  );
}
