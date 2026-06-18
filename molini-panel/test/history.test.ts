import { describe, it, expect } from 'vitest';
import { fetchHistory } from '../src/hass/history';
import type { Hass } from '../src/hass/types';

describe('fetchHistory', () => {
  it('falls back to a mock series when callWS is absent', async () => {
    const pts = await fetchHistory({ states: {} } as Hass, 'sensor.x', 24);
    expect(pts.length).toBeGreaterThan(2);
    expect(pts.every((p) => Number.isFinite(p.v) && Number.isFinite(p.t))).toBe(true);
  });

  it('parses the compressed WS history format', async () => {
    const hass = {
      states: {},
      callWS: async () => ({
        'sensor.x': [
          { s: '10', lu: 1_700_000_000 },
          { s: '20', lu: 1_700_000_900 },
        ],
      }),
    } as unknown as Hass;
    const pts = await fetchHistory(hass, 'sensor.x', 24);
    expect(pts).toEqual([
      { t: 1_700_000_000_000, v: 10 },
      { t: 1_700_000_900_000, v: 20 },
    ]);
  });
});
