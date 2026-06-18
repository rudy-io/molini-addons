// Sous-ensemble minimal de l'objet `hass` injecté par HA dans le custom element.
export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
  last_changed?: string;
  last_updated?: string;
}

export interface Hass {
  states: Record<string, HassEntity>;
  language?: string;
  // Présent en prod (connexion HA) ; absent/mocké en dev.
  callWS?: <T = any>(msg: Record<string, any>) => Promise<T>;
}
