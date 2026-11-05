import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const output = process.argv[2];
if (!output) throw new Error('Pass a new output JavaScript path');
await build({entryPoints: [path.join(root, 'loader.js')], bundle: true, platform: 'neutral', format: 'iife', target: 'es2020', outfile: output});
