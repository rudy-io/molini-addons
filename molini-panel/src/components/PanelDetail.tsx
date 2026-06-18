import type { Hass } from '../hass/types';
import { groupPanels } from '../panels/detect';
import { numState, fmtW } from '../hass/read';

// Borne haute d'un string résidentiel (~400-500 W crête) pour la mini-barre.
const PANEL_MAX_W = 400;

export function PanelDetail({ hass }: { hass: Hass }) {
  const groups = groupPanels(Object.keys(hass.states));
  if (groups.length === 0) return null;

  return (
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {groups.map((g) => (
        <div key={g.key} class="rounded-xl bg-moli-surface border border-moli-border p-3.5">
          <div class="text-[13px] text-moli-muted mb-2.5">{g.label}</div>
          <div class="grid grid-cols-2 gap-2">
            {g.panels.map((p) => {
              const w = numState(hass, p.eid);
              const pct = w == null ? 0 : Math.min(100, Math.round((w / PANEL_MAX_W) * 100));
              return (
                <div key={p.eid} data-panel-tile class="rounded-lg bg-moli-surface2 p-2.5">
                  <div class="text-xs text-moli-muted">{p.name}</div>
                  <div class="text-[17px] font-medium">
                    {fmtW(w)}
                    <span class="text-[11px] text-moli-muted"> W</span>
                  </div>
                  <div class="mt-1.5 h-1 rounded-full bg-moli-border overflow-hidden">
                    <div
                      class={`h-full rounded-full ${pct < 20 ? 'bg-low' : 'bg-solar'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
