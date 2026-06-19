import type { Hass } from './types';

export interface Point {
  t: number; // epoch ms
  v: number; // valeur (W)
}

type Profile = 'solar' | 'load';

// Historique d'une entité via le WS HA. Avec callWS (prod) → vraies données
// (liste vide si l'entité n'a pas d'historique : PAS de fausse courbe). Sans
// callWS (dev) → courbe factice selon le profil.
export async function fetchHistory(
  hass: Hass,
  eid: string,
  hours = 24,
  profile: Profile = 'solar',
): Promise<Point[]> {
  if (hass.callWS) {
    try {
      const end = new Date();
      const start = new Date(end.getTime() - hours * 3600_000);
      const res = await hass.callWS<Record<string, any[]>>({
        type: 'history/history_during_period',
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: [eid],
        minimal_response: true,
        no_attributes: true,
      });
      const series = res?.[eid];
      if (!Array.isArray(series)) return [];
      return series
        .map((s: any) => ({
          t: s.lu != null ? s.lu * 1000 : Date.parse(s.last_updated ?? s.last_changed ?? ''),
          v: Number(s.s ?? s.state),
        }))
        .filter((p) => Number.isFinite(p.v) && Number.isFinite(p.t));
    } catch {
      return [];
    }
  }
  // Dev uniquement (pas de connexion HA).
  return profile === 'load' ? mockLoadCurve(hours) : mockSolarCurve(hours);
}

// Cloche solaire centrée midi.
function mockSolarCurve(hours: number): Point[] {
  return mockCurve(hours, (h) => Math.max(0, Math.exp(-(((h - 13) / 3.2) ** 2)) * 4600 - 60));
}

// Profil de consommation domestique : base + pic matin + pic soir.
function mockLoadCurve(hours: number): Point[] {
  return mockCurve(
    hours,
    (h) =>
      280 + Math.exp(-(((h - 8) / 1.6) ** 2)) * 850 + Math.exp(-(((h - 20) / 2.2) ** 2)) * 1500,
  );
}

function mockCurve(hours: number, fn: (h: number) => number): Point[] {
  const pts: Point[] = [];
  const now = Date.now();
  for (let i = hours * 4; i >= 0; i--) {
    const t = now - i * 15 * 60_000;
    const d = new Date(t);
    const h = d.getHours() + d.getMinutes() / 60;
    pts.push({ t, v: Math.max(0, Math.round(fn(h))) });
  }
  return pts;
}
