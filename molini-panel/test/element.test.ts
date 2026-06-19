import { describe, it, expect } from 'vitest';
import '../src/element'; // enregistre le custom element moli-panel
import { mockHass } from '../src/dev/mockHass';

describe('<moli-panel> custom element', () => {
  it('is registered', () => {
    expect(customElements.get('moli-panel')).toBeTruthy();
  });

  it('renders the app into a shadow root when hass is set', () => {
    const el = document.createElement('moli-panel') as HTMLElement & { hass: unknown };
    document.body.appendChild(el);
    el.hass = mockHass;

    const shadow = el.shadowRoot;
    expect(shadow).toBeTruthy();
    // Le <style> d'injection CSS est présent (son contenu compilé est vérifié
    // sur le bundle de build, pas ici : vitest ne compile pas les imports ?inline).
    expect(shadow!.querySelector('style')).toBeTruthy();
    // App rendue dans le shadow (jauge + installations visibles).
    expect(shadow!.innerHTML).toContain('Production solaire');
    expect(shadow!.innerHTML).toContain('Onduleur SolarMan');
    expect(shadow!.querySelectorAll('[data-panel-tile]').length).toBe(12);
  });
});
