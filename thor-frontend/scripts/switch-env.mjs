/**
 * thor/frontend/scripts/switch-env.mjs
 * Environment switch helper
 * Copies one of the template files (.env.docker, etc.) into
 * .env.local so Vite and the React app point at the correct backend
 * (local runserver vs Docker/Gunicorn). Use via npm scripts.
 */
import { copyFileSync, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Expect a single argument (docker) pointing to .env.<name>
const envName = process.argv[2];

if (!envName) {
  console.error('Usage: node scripts/switch-env.mjs <env-name> (e.g. docker)');
  process.exit(1);
}

if (envName !== 'docker') {
  console.error('[env] Only "docker" is supported. Local dev uses .env.local directly.');
  process.exit(1);
}

// Resolve project root by walking up from the script location
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const templatePath = path.join(projectRoot, `.env.${envName}`);
const targetPath = path.join(projectRoot, '.env.local');

// Guard: template must exist or we abort with a friendly message
if (!existsSync(templatePath)) {
  console.error(`[env] Template ${templatePath} not found.`);
  process.exit(1);
}

// Copy the template into .env.local so Vite picks it up on next start
copyFileSync(templatePath, targetPath);
console.log(`[env] Switched to ${path.basename(templatePath)} → .env.local`);
