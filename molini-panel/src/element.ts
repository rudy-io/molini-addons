import { h, render } from 'preact';
import { App } from './App';
import css from './app.css?inline';

// Custom element chargé par HA via panel_custom (name: moli-panel).
// HA crée <moli-panel> et y affecte la propriété `hass` (states live + WS),
// ré-affectée à chaque update → on re-render l'app Preact.
// Styles isolés dans un shadow DOM (CSS Tailwind compilé injecté).
class MoliPanel extends HTMLElement {
  private _hass: any = null;
  private mountPoint: HTMLDivElement;

  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = css;
    shadow.appendChild(style);
    this.mountPoint = document.createElement('div');
    shadow.appendChild(this.mountPoint);
  }

  set hass(value: any) {
    this._hass = value;
    this.renderApp();
  }
  get hass() {
    return this._hass;
  }

  connectedCallback(): void {
    this.renderApp();
  }

  private renderApp(): void {
    render(h(App, { hass: this._hass ?? { states: {} } }), this.mountPoint);
  }
}

if (!customElements.get('moli-panel')) {
  customElements.define('moli-panel', MoliPanel);
}
