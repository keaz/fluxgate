#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Initialize Edge Server Client (REST)
 *
 * This script creates a backend client for the edge server to use.
 *
 * Usage:
 *   node init-edge-client.js
 *
 * Requirements:
 *   - Backend must be running at http://localhost:8080/api/v1
 *   - Admin user must exist (created during first backend startup)
 */

const API_BASE = process.env.REST_HTTP_URL
  || process.env.API_BASE_URL
  || 'http://localhost:8080/api/v1';
const DEFAULT_PASSWORD = process.env.ADMIN_PASSWORD || 'password123';

// Color codes
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
};

const buildUrl = (pathValue) => {
  if (pathValue.startsWith('http://') || pathValue.startsWith('https://')) return pathValue;
  const base = API_BASE.replace(/\/+$/, '');
  return `${base}${pathValue.startsWith('/') ? pathValue : `/${pathValue}`}`;
};

async function apiJson(pathValue, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(pathValue), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      message = data?.message || data?.error || message;
    } catch {
      // ignore
    }
    const error = new Error(`Request failed (${response.status}): ${message}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

function logStep(message) {
  console.log(`${colors.cyan}▶ ${message}${colors.reset}`);
}

function logSuccess(message) {
  console.log(`${colors.green}✓ ${message}${colors.reset}`);
}

function logError(message) {
  console.error(`${colors.red}✗ ${message}${colors.reset}`);
}

async function createAdminIfNeeded() {
  logStep('Checking for admin user...');

  const input = {
    username: 'admin',
    password: DEFAULT_PASSWORD,
    firstName: 'Admin',
    lastName: 'User',
    email: 'admin@fluxgate.io',
  };

  try {
    const admin = await apiJson('/admins', { method: 'POST', body: input });
    logSuccess(`Created admin: ${admin.username}`);
  } catch (error) {
    if (error.status === 409) {
      logStep('Admin already exists, continuing...');
      return;
    }
    throw error;
  }
}

async function loginAsAdmin() {
  logStep('Logging in as admin...');

  const data = await apiJson('/auth/login', {
    method: 'POST',
    body: {
      username: 'admin',
      password: DEFAULT_PASSWORD,
    },
  });

  logSuccess(`Logged in as: ${data.user.username}`);
  return data.token;
}

async function createPerfTeam(token) {
  logStep('Creating/fetching performance test team...');

  const teams = await apiJson('/teams', { token });
  const existingTeam = teams.find((t) => t.name === 'Performance Test Team');

  if (existingTeam) {
    logSuccess(`Using existing team: ${existingTeam.name} (ID: ${existingTeam.id})`);
    return existingTeam;
  }

  const created = await apiJson('/teams', {
    method: 'POST',
    token,
    body: {
      name: 'Performance Test Team',
      description: 'Team for performance benchmarking',
    },
  });

  logSuccess(`Created team: ${created.name} (ID: ${created.id})`);
  return created;
}

async function createEdgeClient(token, teamId) {
  logStep('Creating edge server client...');

  const client = await apiJson(`/teams/${teamId}/clients`, {
    method: 'POST',
    token,
    body: {
      name: 'Performance Test Edge Server',
      description: 'Edge server for performance testing',
      enabled: true,
      clientType: 'BACKEND',
      webOrigins: [],
    },
  });

  logSuccess(`Created client: ${client.name}`);

  return {
    id: client.id,
    apiKey: client.apiKey,
  };
}

async function updateEdgeConfig(clientId, clientSecret) {
  logStep('Updating edge configuration file...');

  const configPath = path.join(__dirname, 'config', 'edge-config.toml');
  let config = fs.readFileSync(configPath, 'utf8');

  config = config.replace(
    /client_id = ".+"/,
    `client_id = "${clientId}"`
  );
  config = config.replace(
    /client_secret = ".+"/,
    `client_secret = "${clientSecret}"`
  );

  fs.writeFileSync(configPath, config);
  logSuccess('Edge configuration updated');
}

async function main() {
  try {
    await createAdminIfNeeded();
    const token = await loginAsAdmin();
    const team = await createPerfTeam(token);
    const client = await createEdgeClient(token, team.id);
    await updateEdgeConfig(client.id, client.apiKey);

    console.log('');
    logSuccess('Edge client initialization complete!');
    console.log(`${colors.blue}Client ID:${colors.reset} ${client.id}`);
    console.log(`${colors.blue}Client Secret:${colors.reset} ${client.apiKey}`);
    console.log('');
  } catch (error) {
    logError(error.message);
    process.exit(1);
  }
}

main();
