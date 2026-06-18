import { render } from 'preact';
import { App } from '../App';
import '../app.css';

// Task 3 remplace ce stub par le vrai mock (fixtures Carole).
const mockHass: any = { states: {} };

render(<App hass={mockHass} />, document.getElementById('app')!);
