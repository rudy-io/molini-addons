// Détection des panneaux PV à partir des entity_id HA.
// Port TS de molini-agent/molini_agent/panel_detail.py (0.7.0), enrichi du
// regroupement par INSTALLATION (et non par onduleur individuel) : chez un
// client il peut y avoir plusieurs onduleurs d'une même marque (ex SolarMan
// `inverter` + `inverter_2`) ou plusieurs micro-onduleurs (IzyPower) qui
// forment UNE installation. On regroupe par marque.

const PV_RE = /^(?<prefix>.+?)_pv(?<n>\d+)(?:_power)?$/;
// Onduleur string SolarMan : sensor.inverter, sensor.inverter_2, …
const SOLARMAN_RE = /(?:^|\.)inverter(?:_\d+)?$/;

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

// Marque/installation déduite du préfixe (null = onduleur non reconnu → son
// propre groupe).
function brandOf(prefix: string): 'solarman' | 'izypower' | null {
  const p = prefix.toLowerCase();
  if (p.includes('izypower')) return 'izypower';
  if (SOLARMAN_RE.test(p)) return 'solarman';
  return null;
}

const BRAND_LABEL: Record<'solarman' | 'izypower', string> = {
  solarman: 'Onduleur SolarMan',
  izypower: 'Micro-onduleurs IzyPower',
};

export interface Panel {
  name: string; // P1, P2…
  eid: string;
}

export interface PanelGroup {
  key: string;
  label: string;
  panels: Panel[];
}

// Regroupe les strings par installation. SolarMan (tous les `inverter*`) et
// IzyPower (tous les `izypower*`) forment chacun UN groupe ; un onduleur de
// marque inconnue garde son propre groupe.
export function groupPanels(entityIds: string[]): PanelGroup[] {
  const byPrefix = detectPanels(entityIds);
  const groups = new Map<string, { label: string; eids: string[] }>();
  let unknown = 0;

  for (const prefix of Object.keys(byPrefix).sort()) {
    const brand = brandOf(prefix);
    const key = brand ?? `other:${prefix}`;
    if (!groups.has(key)) {
      groups.set(key, { label: brand ? BRAND_LABEL[brand] : inverterLabel(prefix, unknown++), eids: [] });
    }
    groups.get(key)!.eids.push(...byPrefix[prefix]);
  }

  const rank = (k: string) => (k === 'solarman' ? 0 : k === 'izypower' ? 1 : 2);
  return [...groups.entries()]
    .sort((a, b) => rank(a[0]) - rank(b[0]) || a[0].localeCompare(b[0]))
    .map(([key, g]) => ({
      key,
      label: g.label,
      panels: g.eids.map((eid, i) => ({ name: `P${i + 1}`, eid })),
    }));
}
