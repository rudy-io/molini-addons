import type { Hass } from './types';

// Lit l'état numérique d'une entité (null si absente / non numérique).
export function numState(hass: Hass, eid: string): number | null {
  const e = hass.states[eid];
  if (!e) return null;
  const n = Number(e.state);
  return Number.isFinite(n) ? n : null;
}

export function fmtW(n: number | null): string {
  return n == null ? '—' : Math.round(n).toLocaleString('fr-FR');
}

export function fmtKwh(n: number | null): string {
  return n == null ? '—' : n.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
}
