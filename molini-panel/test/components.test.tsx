import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/preact';
import { PanelDetail } from '../src/components/PanelDetail';
import { Gauge } from '../src/components/Gauge';
import { mockHass } from '../src/dev/mockHass';

afterEach(cleanup);

describe('PanelDetail', () => {
  it('renders 2 installations (SolarMan + IzyPower) and 12 panel modules', () => {
    const { container } = render(<PanelDetail hass={mockHass} />);
    expect(container.textContent).toContain('Onduleur SolarMan');
    expect(container.textContent).toContain('Micro-onduleurs IzyPower');
    expect(container.querySelectorAll('[data-panel-tile]').length).toBe(12);
  });
});

describe('Gauge', () => {
  it('shows the value + label when available', () => {
    const { container } = render(
      <Gauge value={1161} max={5000} label="Production solaire" color="#1d9e75" />,
    );
    expect(container.textContent).toContain('Production solaire');
    expect(container.textContent).toMatch(/1.?161/);
  });

  it('shows a muted dash + label when the value is null', () => {
    const { container } = render(
      <Gauge
        value={null}
        max={5000}
        label="Consommation maison"
        color="#378add"
        mutedLabel="non suivie"
      />,
    );
    expect(container.textContent).toContain('Consommation maison');
    expect(container.textContent).toContain('—');
    expect(container.textContent).toContain('non suivie');
  });
});
