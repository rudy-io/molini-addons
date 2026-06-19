import type { Hass } from '../hass/types';
import { groupPanels } from '../panels/detect';
import { numState } from '../hass/read';
import { PanelModule } from './PanelModule';

// Borne haute d'un string résidentiel (~400-500 W crête) pour le remplissage.
const PANEL_MAX_W = 400;

export function PanelDetail({ hass }: { hass: Hass }) {
  const groups = groupPanels(Object.keys(hass.states));
  if (groups.length === 0) return null;

  return (
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {groups.map((g) => (
        <div key={g.key} class="rounded-xl bg-moli-surface border border-moli-border p-3.5">
          <div class="text-[13px] text-moli-muted mb-2.5">
            {g.label} <span class="text-moli-muted/70">· {g.panels.length} panneaux</span>
          </div>
          <div class="grid grid-cols-3 gap-2">
            {g.panels.map((p) => (
              <PanelModule
                key={p.eid}
                id={p.eid.replace(/[^a-z0-9]/gi, '')}
                name={p.name}
                watts={numState(hass, p.eid)}
                max={PANEL_MAX_W}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
