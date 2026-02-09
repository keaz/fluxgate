#!/usr/bin/env node

/**
 * FluxGate Test Data Population Script (REST)
 *
 * This script seeds a minimal but useful dataset using REST endpoints.
 *
 * Usage:
 *   node populate_test_data.js
 *
 * Requirements:
 *   - Backend running at http://localhost:8080/api/v1
 */

const API_BASE = process.env.REST_HTTP_URL
  || process.env.API_BASE_URL
  || 'http://localhost:8080/api/v1';

const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'password123';

const ROLE_IDS = {
  approver: '00000000-0000-0000-0000-000000000001',
  requester: '00000000-0000-0000-0000-000000000002',
  teamAdmin: '00000000-0000-0000-0000-000000000003',
};

const TEAM_NAME = process.env.SEED_TEAM_NAME || 'E-Commerce Team';
const PIPELINE_NAME = `${TEAM_NAME} Pipeline`;
const CLIENT_NAME = `${TEAM_NAME} Edge Client`;
const APPROVAL_POLICY_NAME = `${TEAM_NAME} Deploy Policy`;

const ENVIRONMENTS = [
  { name: 'E-Commerce-Dev', type: 'Development' },
  { name: 'E-Commerce-Staging', type: 'Staging' },
  { name: 'E-Commerce-Prod', type: 'Production' },
];

const FEATURE_KEYS = [
  'NewCheckoutFlow',
  'PaymentMethodApplePay',
  'ProductRecommendations',
  'GiftWrapping',
  'ExpressShipping',
  'PremiumCheckout',
  'BulkOrderDiscount',
  'RegionalPricing',
  'LoyaltyProgram',
  'SeasonalPromotions',
];

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
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

const logStep = (message) => {
  console.log(`${colors.cyan}▶ ${message}${colors.reset}`);
};

const logSuccess = (message) => {
  console.log(`${colors.green}✓ ${message}${colors.reset}`);
};

const logWarn = (message) => {
  console.log(`${colors.yellow}⚠ ${message}${colors.reset}`);
};

const logError = (message) => {
  console.error(`${colors.red}✗ ${message}${colors.reset}`);
};

async function createAdminIfNeeded() {
  logStep('Ensuring admin user exists...');

  const input = {
    username: ADMIN_USERNAME,
    password: ADMIN_PASSWORD,
    firstName: 'Admin',
    lastName: 'User',
    email: 'admin@fluxgate.io',
  };

  try {
    const admin = await apiJson('/admins', { method: 'POST', body: input });
    logSuccess(`Created admin: ${admin.username}`);
  } catch (error) {
    if (error.status === 409) {
      logWarn('Admin already exists, continuing...');
      return;
    }
    throw error;
  }
}

async function loginAsAdmin() {
  logStep('Logging in as admin...');
  const data = await apiJson('/auth/login', {
    method: 'POST',
    body: { username: ADMIN_USERNAME, password: ADMIN_PASSWORD },
  });
  logSuccess(`Logged in as: ${data.user.username}`);
  return data;
}

async function assignAdminRoles(token, userId) {
  logStep('Assigning Requester + Approver roles to admin...');
  try {
    await apiJson(`/users/${userId}/roles`, {
      method: 'POST',
      token,
      body: { roleIds: [ROLE_IDS.requester, ROLE_IDS.approver, ROLE_IDS.teamAdmin] },
    });
    logSuccess('Roles assigned to admin.');
  } catch (error) {
    logWarn(`Role assignment skipped: ${error.message}`);
  }
}

async function getOrCreateTeam(token) {
  logStep(`Ensuring team "${TEAM_NAME}" exists...`);
  const teams = await apiJson('/teams', { token });
  const existing = teams.find((t) => t.name === TEAM_NAME);
  if (existing) {
    logSuccess(`Using team: ${existing.name}`);
    return existing;
  }

  const created = await apiJson('/teams', {
    method: 'POST',
    token,
    body: { name: TEAM_NAME, description: `${TEAM_NAME} seed data` },
  });
  logSuccess(`Created team: ${created.name}`);
  return created;
}

async function getOrCreateEnvironment(token, teamId, env) {
  const query = new URLSearchParams({ name: env.name, offset: '0', limit: '1' }).toString();
  const existing = await apiJson(`/teams/${teamId}/environments?${query}`, { token });
  if (existing.items.length > 0) {
    return existing.items[0];
  }

  const created = await apiJson(`/teams/${teamId}/environments`, {
    method: 'POST',
    token,
    body: { name: env.name, active: true, environmentType: env.type },
  });
  logSuccess(`Created environment: ${created.name}`);
  return created;
}

function buildPipelineStages(environments) {
  return environments.map((env, idx) => ({
    environmentId: env.id,
    orderIndex: idx,
    position: JSON.stringify({ x: 200 + idx * 180, y: 120 }),
  }));
}

function buildRelationships(stageCount) {
  if (stageCount <= 1) return [];
  const rels = [];
  for (let i = 0; i < stageCount - 1; i += 1) {
    rels.push({ sourceId: i, targetId: i + 1 });
  }
  return rels;
}

async function getOrCreatePipeline(token, teamId, environments) {
  logStep(`Ensuring pipeline "${PIPELINE_NAME}" exists...`);
  const query = new URLSearchParams({ name: PIPELINE_NAME, offset: '0', limit: '1' }).toString();
  const existing = await apiJson(`/teams/${teamId}/pipelines?${query}`, { token });
  if (existing.items.length > 0) {
    logSuccess(`Using pipeline: ${existing.items[0].name}`);
    return existing.items[0];
  }

  const created = await apiJson(`/teams/${teamId}/pipelines`, {
    method: 'POST',
    token,
    body: {
      name: PIPELINE_NAME,
      stages: buildPipelineStages(environments),
      relationships: buildRelationships(environments.length),
    },
  });
  logSuccess(`Created pipeline: ${created.name}`);
  return created;
}

async function getOrCreateApprovalPolicy(token, teamId) {
  const policies = await apiJson(`/teams/${teamId}/approval-policies`, { token });
  const existing = policies.find((p) => p.name === APPROVAL_POLICY_NAME);
  if (existing) {
    logSuccess(`Using approval policy: ${existing.name}`);
    return existing;
  }

  const created = await apiJson(`/teams/${teamId}/approval-policies`, {
    method: 'POST',
    token,
    body: {
      name: APPROVAL_POLICY_NAME,
      description: 'Auto-created policy for seed deployments',
      appliesTo: 'all',
      environmentIds: null,
      requiredApprovers: 1,
      approverRoleIds: [ROLE_IDS.approver],
      autoApproveAfterHours: null,
      enabled: true,
    },
  });
  logSuccess(`Created approval policy: ${created.name}`);
  return created;
}

function pickClientEnvironmentId(environments) {
  const production = environments.find((env) => String(env.environmentType || env.type || '').toUpperCase() === 'PRODUCTION');
  if (production?.id) return production.id;
  return environments[environments.length - 1]?.id || environments[0]?.id;
}

async function getOrCreateClient(token, teamId, environments) {
  logStep(`Ensuring client "${CLIENT_NAME}" exists...`);
  const query = new URLSearchParams({ name: CLIENT_NAME, offset: '0', limit: '1' }).toString();
  const existing = await apiJson(`/teams/${teamId}/clients?${query}`, { token });
  if (existing.items.length > 0) {
    logSuccess(`Using client: ${existing.items[0].name}`);
    return existing.items[0];
  }

  const environmentId = pickClientEnvironmentId(environments);
  if (!environmentId) {
    throw new Error('No environments available to bind client environmentId');
  }

  const created = await apiJson(`/teams/${teamId}/clients`, {
    method: 'POST',
    token,
    body: {
      name: CLIENT_NAME,
      description: 'Seeded backend client for edge server tests',
      enabled: true,
      clientType: 'BACKEND',
      webOrigins: [],
      environmentId,
    },
  });
  logSuccess(`Created client: ${created.name}`);
  return created;
}

async function getOrCreateFeature(token, teamId, environments, key) {
  try {
    const created = await apiJson(`/teams/${teamId}/features`, {
      method: 'POST',
      token,
      body: {
        key,
        description: `Seeded feature ${key}`,
        featureType: 'SIMPLE',
        enabled: true,
        dependencies: [],
        relationships: buildRelationships(environments.length),
        stages: environments.map((env, idx) => ({
          environmentId: env.id,
          orderIndex: idx,
          position: JSON.stringify({ x: 200 + idx * 180, y: 120 }),
          bucketingKey: null,
        })),
        variants: null,
      },
    });
    logSuccess(`Created feature: ${key}`);
    return created;
  } catch (error) {
    if (error.status !== 409) throw error;
    const query = new URLSearchParams({ name: key, offset: '0', limit: '1' }).toString();
    const list = await apiJson(`/teams/${teamId}/features?${query}`, { token });
    const existing = list.items[0];
    if (!existing) throw error;
    const full = await apiJson(`/features/${existing.id}`, { token });
    logWarn(`Using existing feature: ${key}`);
    return full;
  }
}

async function requestStageChange(token, stageId, request) {
  return apiJson(`/stages/${stageId}/request-change`, {
    method: 'POST',
    token,
    body: { request },
  });
}

async function approveRequest(token, requestId) {
  return apiJson(`/approval-requests/${requestId}/approve`, {
    method: 'POST',
    token,
    body: { comment: 'Auto-approved by seed script' },
  });
}

async function deployStage(token, stage) {
  if (stage.status === 'DEPLOYED') {
    return;
  }

  let pendingId = null;
  try {
    const result = await requestStageChange(token, stage.id, 'DEPLOYMENT_REQUESTED');
    pendingId = result.pendingApprovalRequestId || null;
  } catch (error) {
    if (error.status !== 400) throw error;
  }

  if (pendingId) {
    await approveRequest(token, pendingId);
  }

  try {
    await requestStageChange(token, stage.id, 'DEPLOYED');
  } catch (error) {
    logWarn(`Stage ${stage.id} deploy skipped: ${error.message}`);
  }
}

async function main() {
  try {
    console.log(`${colors.bright}${colors.blue}FluxGate REST Seed${colors.reset}`);
    await createAdminIfNeeded();
    const login = await loginAsAdmin();
    await assignAdminRoles(login.token, login.user.id);

    const team = await getOrCreateTeam(login.token);
    const environments = [];
    for (const env of ENVIRONMENTS) {
      environments.push(await getOrCreateEnvironment(login.token, team.id, env));
    }

    await getOrCreateApprovalPolicy(login.token, team.id);
    await getOrCreatePipeline(login.token, team.id, environments);
    const client = await getOrCreateClient(login.token, team.id, environments);

    const features = [];
    for (const key of FEATURE_KEYS) {
      const feature = await getOrCreateFeature(login.token, team.id, environments, key);
      features.push(feature);
    }

    logStep('Deploying feature stages...');
    for (const feature of features) {
      if (!feature.stages) continue;
      for (const stage of feature.stages) {
        await deployStage(login.token, stage);
      }
    }

    console.log('');
    console.log(`${colors.bright}${colors.green}Seed completed successfully!${colors.reset}`);
    console.log(`${colors.cyan}Summary:${colors.reset}`);
    console.log(`  - Team: ${team.name} (${team.id})`);
    console.log(`  - Environments: ${environments.map((e) => e.id).join(', ')}`);
    console.log(`  - Features: ${features.length}`);
    console.log(`  - Client ID: ${client.id}`);
    console.log(`  - Client Secret: ${client.apiKey}`);
    console.log('');
  } catch (error) {
    logError(`Fatal error: ${error.message}`);
    process.exit(1);
  }
}

main();
