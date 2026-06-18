import type { Hass } from './hass/types';
import { EnergyScreen } from './screens/EnergyScreen';

export function App({ hass }: { hass: Hass }) {
  return <EnergyScreen hass={hass} />;
}
