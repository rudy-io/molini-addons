import type { Hass } from '../hass/types';

// Placeholder (Task 4). Le vrai graph SVG + historique WS arrive en Task 5.
export function History24h({ hass }: { hass: Hass }) {
  void hass;
  return (
    <div class="rounded-xl bg-moli-surface border border-moli-border p-4 h-40 flex items-center justify-center text-moli-muted text-sm">
      Graphique 24 h
    </div>
  );
}
