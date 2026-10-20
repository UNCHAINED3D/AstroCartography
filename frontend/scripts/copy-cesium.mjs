// Copies Cesium's static runtime assets (Web Workers, icons, SVG themes) into
// the Vite `public` folder so that `window.CESIUM_BASE_URL` can point at them.
// Run automatically via `postinstall` (so `npm install` refreshes them) and at
// the start of `npm run build` (so a fresh clone that skipped install still works).
import { cpSync, existsSync, rmSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const from = resolve(root, 'node_modules/cesium/Build/Cesium');
const to = resolve(root, 'public/cesium');

if (!existsSync(from)) {
  console.warn('[copy-cesium] node_modules/cesium/Build/Cesium not found. Run `npm install` first.');
  process.exit(0);
}

rmSync(to, { recursive: true, force: true });
cpSync(from, to, { recursive: true, force: true });
console.log(`[copy-cesium] Copied Cesium static assets -> public/cesium (${from})`);