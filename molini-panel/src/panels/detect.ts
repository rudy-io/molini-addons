// Détection des panneaux PV à partir des entity_id HA, groupés par onduleur.
// Port TS de molini-agent/molini_agent/panel_detail.py (0.7.0).
// Un capteur de string finit par _pvN (IzyPower) ou _pvN_power (SolarMan) ;
// tout le reste est exclu (ex sensor.inverter_2_power = total AC).

const PV_RE = /^(?<prefix>.+?)_pv(?<n>\d+)(?:_power)?$/;

export function detectPanels(entityIds: string[]): Record<string, string[]> {
  const groups: Record<string, string[]> = {};
  for (const eid of entityIds) {
    if (!eid.startsWith('sensor.')) continue;
    const m = PV_RE.exec(eid);
    if (!m?.groups) continue;
    (groups[m.groups.prefix] ??= []).push(eid);
  }
  for (const key of Object.keys(groups)) {
    groups[key].sort(
      (a, b) => Number(PV_RE.exec(a)!.groups!.n) - Number(PV_RE.exec(b)!.groups!.n),
    );
  }
  return groups;
}

function isMicro(prefix: string): boolean {
  const p = prefix.toLowerCase();
  return p.includes('izypower') || p.includes('micro');
}

export function inverterLabel(prefix: string, index: number): string {
  return `${isMicro(prefix) ? 'Micro-onduleur' : 'Onduleur'} ${index + 1}`;
}

export interface Panel {
  name: string; // P1, P2…
  eid: string;
}

export interface PanelGroup {
  key: string; // préfixe onduleur (sensor. inclus)
  label: string; // libellé lisible, numéroté par type
  panels: Panel[];
}

export function groupPanels(entityIds: string[]): PanelGroup[] {
  const groups = detectPanels(entityIds);
  const counters: Record<'micro' | 'string', number> = { micro: 0, string: 0 };
  return Object.keys(groups)
    .sort()
    .map((key) => {
      const kind = isMicro(key) ? 'micro' : 'string';
      const label = inverterLabel(key, counters[kind]++);
      return {
        key,
        label,
        panels: groups[key].map((eid, i) => ({ name: `P${i + 1}`, eid })),
      };
    });
}
