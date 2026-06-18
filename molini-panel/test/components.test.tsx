import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/preact';
import { PanelDetail } from '../src/components/PanelDetail';
import { ConsoTile } from '../src/components/ConsoTile';
import { mockHass } from '../src/dev/mockHass';
import type { Hass } from '../src/hass/types';

afterEach(cleanup);

describe('PanelDetail', () => {
  it('renders the 4 inverter labels and 9 panel tiles from a hass', () => {
    const { getByText, container } = render(<PanelDetail hass={mockHass} />);
    expect(getByText('Onduleur 1')).toBeTruthy();
    expect(getByText('Onduleur 2')).toBeTruthy();
    expect(getByText('Micro-onduleur 1')).toBeTruthy();
    expect(getByText('Micro-onduleur 2')).toBeTruthy();
    expect(container.querySelectorAll('[data-panel-tile]').length).toBe(9);
  });
});

describe('ConsoTile', () => {
  it('renders nothing when the conso sensor is absent', () => {
    const { container } = render(<ConsoTile hass={mockHass} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the value when the conso sensor exists', () => {
    const withConso: Hass = {
      states: {
        ...mockHass.states,
        'sensor.molini_consommation_maison': {
          entity_id: 'sensor.molini_consommation_maison',
          state: '742',
          attributes: {},
        },
      },
    };
    const { getByText } = render(<ConsoTile hass={withConso} />);
    expect(getByText('Consommation maison')).toBeTruthy();
    expect(getByText(/742/)).toBeTruthy();
  });
});
