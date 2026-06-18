import { mkdirSync, copyFileSync } from 'node:fs';

const dstDir = '../molini-agent/rootfs/usr/share/molini/panel';
mkdirSync(dstDir, { recursive: true });
copyFileSync('dist/moli-panel.js', `${dstDir}/moli-panel.js`);
console.log(`copied dist/moli-panel.js → ${dstDir}/moli-panel.js`);
