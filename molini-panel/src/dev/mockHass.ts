import type { Hass, HassEntity } from '../hass/types';

// Fixtures de l'install réelle de Carole (4 onduleurs / 9 strings), valeurs
// façon screenshot (production de fin de journée). Sert au dev sans box live.

const states: Record<string, HassEntity> = {};

function add(entity_id: string, state: string, attributes: Record<string, any> = {}): void {
  states[entity_id] = { entity_id, state, attributes };
}

const W = { unit_of_measurement: 'W', device_class: 'power' };
const KWH = { unit_of_measurement: 'kWh', device_class: 'energy' };

// 9 strings — 2 SolarMan (inverter, inverter_2) + 2 IzyPower (aa2e, c3e6)
add('sensor.inverter_pv1_power', '124', W);
add('sensor.inverter_pv2_power', '131', W);
add('sensor.inverter_2_pv1_power', '133', W);
add('sensor.inverter_2_pv2_power', '143', W);
add('sensor.inverter_2_pv3_power', '130', W);
add('sensor.inverter_2_pv4_power', '136', W);
add('sensor.izypower_cloud_maison_35486_55180000aa2e_pv1', '85', W);
add('sensor.izypower_cloud_maison_35486_55180000aa2e_pv2', '28', W);
add('sensor.izypower_cloud_maison_35486_60580000c3e6_pv1', '53', W);

// Bruit (doit être ignoré par la détection) : total AC + une lumière
add('sensor.inverter_2_power', '542', W);
add('light.salon', 'on', { friendly_name: 'Salon' });

// Totaux molini_* (template sensors posés par l'agent)
add('sensor.molini_solaire_production', '1161', { ...W, friendly_name: 'MOLINI Solaire Production' });
add('sensor.molini_solaire_production_aujourd_hui', '45.27', KWH);
add('sensor.molini_solaire_production_totale', '5305.3', KWH);

// Compteur Linky (index)
add('sensor.molini_index_hc', '33450.73', KWH);
add('sensor.molini_index_hp', '35803.22', KWH);

// Pas de sensor.molini_consommation_maison → la tuile conso reste masquée
// (Linky pas encore en TIC standard chez Carole).

export const mockHass: Hass = {
  states,
  language: 'fr',
  async callWS<T = any>(): Promise<T> {
    return null as unknown as T;
  },
};
