import { describe, it, expect } from 'vitest';
import { detectPanels, inverterLabel, groupPanels } from '../src/panels/detect';

const CAROLE = [
  'sensor.inverter_pv1_power',
  'sensor.inverter_pv2_power',
  'sensor.inverter_2_pv1_power',
  'sensor.inverter_2_pv2_power',
  'sensor.inverter_2_pv3_power',
  'sensor.inverter_2_pv4_power',
  'sensor.izypower_cloud_maison_35486_55180000aa2e_pv1',
  'sensor.izypower_cloud_maison_35486_55180000aa2e_pv2',
  'sensor.izypower_cloud_maison_35486_60580000c3e6_pv1',
  'sensor.light_salon',
  'sensor.inverter_2_power', // bruit : total AC, ne doit pas matcher
];

describe('detectPanels', () => {
  it('groups PV sensors by inverter prefix', () => {
    const g = detectPanels(CAROLE);
    expect(g['sensor.inverter']).toEqual([
      'sensor.inverter_pv1_power',
      'sensor.inverter_pv2_power',
    ]);
    expect(g['sensor.inverter_2']).toHaveLength(4);
    expect(g).toHaveProperty('sensor.izypower_cloud_maison_35486_55180000aa2e');
    expect(Object.keys(g)).toHaveLength(4); // 2 SolarMan + 2 IzyPower
    const flat = Object.values(g).flat();
    expect(flat).not.toContain('sensor.inverter_2_power');
    expect(flat).not.toContain('sensor.light_salon');
  });

  it('returns {} when there is no PV sensor', () => {
    expect(detectPanels(['sensor.temperature'])).toEqual({});
  });

  it('sorts strings numerically, not lexically', () => {
    const g = detectPanels(['sensor.x_pv2_power', 'sensor.x_pv10_power', 'sensor.x_pv1_power']);
    expect(g['sensor.x']).toEqual([
      'sensor.x_pv1_power',
      'sensor.x_pv2_power',
      'sensor.x_pv10_power',
    ]);
  });
});

describe('inverterLabel', () => {
  it('labels string inverters', () => {
    expect(inverterLabel('inverter', 0)).toBe('Onduleur 1');
    expect(inverterLabel('inverter_2', 1)).toBe('Onduleur 2');
  });
  it('labels micro-inverters from the prefix content', () => {
    expect(inverterLabel('sensor.izypower_cloud_maison_35486_55180000aa2e', 0)).toBe(
      'Micro-onduleur 1',
    );
  });
});

describe('groupPanels', () => {
  it('numbers inverters per type (no "Micro-onduleur 3")', () => {
    const groups = groupPanels(CAROLE);
    expect(groups.map((x) => x.label)).toEqual([
      'Onduleur 1',
      'Onduleur 2',
      'Micro-onduleur 1',
      'Micro-onduleur 2',
    ]);
  });
  it('exposes P-named panels with their real eids', () => {
    const ond2 = groupPanels(CAROLE).find((g) => g.label === 'Onduleur 2')!;
    expect(ond2.panels.map((p) => p.name)).toEqual(['P1', 'P2', 'P3', 'P4']);
    expect(ond2.panels[0].eid).toBe('sensor.inverter_2_pv1_power');
  });
  it('returns [] when there is no PV', () => {
    expect(groupPanels(['sensor.x'])).toEqual([]);
  });
});
