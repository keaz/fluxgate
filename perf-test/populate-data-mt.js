#!/usr/bin/env node

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

/**
 * Multi-threaded seeding wrapper (REST)
 *
 * For simplicity, this delegates to populate-data.js. The REST API
 * already supports high throughput, and this keeps the seed path unified.
 */

const scriptPath = fileURLToPath(new URL('./populate-data.js', import.meta.url));
const args = process.argv.slice(2);

const child = spawn(process.execPath, [scriptPath, ...args], { stdio: 'inherit' });
child.on('exit', (code) => {
  process.exit(code ?? 0);
});
