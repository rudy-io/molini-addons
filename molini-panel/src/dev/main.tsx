import { render } from 'preact';
import { App } from '../App';
import { mockHass } from './mockHass';
import '../app.css';

render(<App hass={mockHass} />, document.getElementById('app')!);
