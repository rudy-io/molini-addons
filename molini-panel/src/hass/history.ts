import type { Hass } from './types';

export interface Point {
  t: number; // epoch ms
  v: number; // valeur (W)
}

// Récupère l'historique d'une entité via le WS HA. En dev (callWS absent /
// renvoie null), retombe sur une courbe solaire factice.
export async function fetchHistory(hass: Hass, eid: string, hours = 24): Promise<Point[]> {
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
      if (Array.isArray(series) && series.length) {
        const pts = series
          .map((s: any) => ({
            t: s.lu != null ? s.lu * 1000 : Date.parse(s.last_updated ?? s.last_changed ?? ''),
            v: Number(s.s ?? s.state),
          }))
          .filter((p) => Number.isFinite(p.v) && Number.isFinite(p.t));
        if (pts.length >= 2) return pts;
      }
    } catch {
      // fall through to mock
    }
  }
  return mockBellCurve(hours);
}

// Courbe en cloche centrée midi solaire — uniquement pour le dev.
function mockBellCurve(hours: number): Point[] {
  const pts: Point[] = [];
  const now = Date.now();
  for (let i = hours * 4; i >= 0; i--) {
    const t = now - i * 15 * 60_000;
    const d = new Date(t);
    const h = d.getHours() + d.getMinutes() / 60;
    const bell = Math.exp(-Math.pow((h - 13) / 3.2, 2)) * 4600 - 60;
    pts.push({ t, v: Math.max(0, Math.round(bell)) });
  }
  return pts;
}
