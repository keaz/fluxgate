#!/usr/bin/env node

/**
 * FluxGate Performance Test Data Population Script (REST)
 *
 * This script populates the database with features for performance testing.
 *
 * Usage:
 *   node populate-data.js [--features=1000] [--batch-size=1] [--start=0]
 */

const API_BASE = process.env.REST_HTTP_URL
  || process.env.API_BASE_URL
  || 'http://localhost:8080/api/v1';
const DEFAULT_PASSWORD = process.env.ADMIN_PASSWORD || 'password123';

// Parse command line arguments
const args = process.argv.slice(2);
const TOTAL_FEATURES = parseInt(args.find((a) => a.startsWith('--features='))?.split('=')[1] || '1000', 10);
const BATCH_SIZE = parseInt(args.find((a) => a.startsWith('--batch-size='))?.split('=')[1] || '1', 10);
const START_INDEX = parseInt(args.find((a) => a.startsWith('--start='))?.split('=')[1] || '0', 10);

// Feature distribution
const SIMPLE_FEATURE_RATIO = 0.7;
const SIMPLE_FEATURES = Math.floor(TOTAL_FEATURES * SIMPLE_FEATURE_RATIO);

const ROLE_IDS = {
  approver: '00000000-0000-0000-0000-000000000001',
  requester: '00000000-0000-0000-0000-000000000002',
};

const TEAM_NAME = 'Performance Test Team';
const PIPELINE_NAME = 'Perf-Test-Pipeline';
const ENVIRONMENT_NAME = 'Perf-Test-Prod';
const APPROVAL_POLICY_NAME = 'Perf Test Deploy Policy';

// Color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
};

let createdFeaturesCount = 0;
let startTime = Date.now();

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
    const text = await response.text().catch(() => '');
    if (text) {
      try {
        const data = JSON.parse(text);
        message = data?.message || data?.error || message;
      } catch {
        // Non-JSON error body (e.g. serde deserialize errors)
        message = text;
      }
    }
    const error = new Error(`Request failed (${response.status}): ${message}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

function logStep(message, isSubstep = false) {
  const prefix = isSubstep ? '  →' : '▶';
  console.log(`${colors.cyan}${prefix} ${message}${colors.reset}`);
}

function logSuccess(message) {
  console.log(`${colors.green}✓ ${message}${colors.reset}`);
}

function logError(message) {
  console.error(`${colors.red}✗ ${message}${colors.reset}`);
}

function logProgress(current, total, message) {
  const percentage = ((current / total) * 100).toFixed(2);
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  const rate = (current / (elapsed || 1)).toFixed(1);
  console.log(
    `${colors.magenta}Progress: ${current}/${total} (${percentage}%) | ${rate} features/sec | ${elapsed}s elapsed | ${message}${colors.reset}`
  );
}

async function createAdminIfNeeded() {
  logStep('Creating initial admin account...');

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
    return admin;
  } catch (error) {
    if (error.status === 409) {
      logStep('Admin account already exists, continuing...', true);
      return null;
    }
    if (error.status === 401 || error.status === 403) {
      const status = await apiJson('/auth/status');
      if (status?.adminConfigured) {
        logStep('Admin bootstrap already completed, continuing...', true);
        return null;
      }
    }
    throw error;
  }
}

async function loginAsAdmin() {
  logStep('Logging in as admin...');

  const data = await apiJson('/auth/login', {
    method: 'POST',
    body: { username: 'admin', password: DEFAULT_PASSWORD },
  });

  logSuccess(`Logged in as: ${data.user.username}`);
  return { token: data.token, userId: data.user.id };
}

async function assignRolesToAdmin(token, userId) {
  logStep('Assigning Approver and Requester roles to admin...');
  try {
    const roles = await apiJson(`/users/${userId}/roles`, {
      method: 'POST',
      token,
      body: { roleIds: [ROLE_IDS.approver, ROLE_IDS.requester] },
    });
    const roleNames = roles.map((r) => r.name).join(', ');
    logSuccess(`Assigned roles: ${roleNames}`);
    return roles;
  } catch (error) {
    logStep('Roles might already be assigned, continuing...', true);
    return null;
  }
}

async function createPerfTeam(token) {
  logStep('Creating performance test team...');

  const teams = await apiJson('/teams', { token });
  const existing = teams.find((t) => t.name === TEAM_NAME);
  if (existing) {
    logSuccess(`Using existing team: ${existing.name} (ID: ${existing.id})`);
    return existing;
  }

  const created = await apiJson('/teams', {
    method: 'POST',
    token,
    body: {
      name: TEAM_NAME,
      description: 'Team for performance benchmarking with 1M features',
    },
  });
  logSuccess(`Created team: ${created.name} (ID: ${created.id})`);
  return created;
}

async function createContexts(token, team) {
  logStep('Creating test contexts...');

  const contexts = [
    { key: 'userId', valueCount: 100 },
    { key: 'region', entries: ['us-east', 'us-west', 'eu-west', 'eu-central', 'ap-south', 'ap-northeast', 'sa-east'] },
    { key: 'tier', entries: ['free', 'basic', 'pro', 'enterprise'] },
    { key: 'userRole', entries: ['viewer', 'editor', 'admin', 'owner'] },
    { key: 'deviceType', entries: ['mobile', 'tablet', 'desktop', 'tv'] },
    { key: 'osType', entries: ['ios', 'android', 'windows', 'macos', 'linux'] },
    { key: 'appVersion', entries: ['v1.0', 'v1.1', 'v1.2', 'v2.0', 'v2.1'] },
    { key: 'language', entries: ['en', 'es', 'fr', 'de', 'ja', 'zh', 'pt', 'ru'] },
    { key: 'country', entries: ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR'] },
    { key: 'beta', entries: ['true', 'false'] },
  ];

  const createdContexts = [];

  for (const context of contexts) {
    try {
      const entries = context.entries || Array.from({ length: context.valueCount }, (_, i) => `${context.key}-${i}`);
      const input = { key: context.key, entries };

      const data = await apiJson(`/teams/${team.id}/contexts`, {
        method: 'POST',
        token,
        body: input,
      });
      createdContexts.push({ ...context, id: data.id, entries });
      logSuccess(`Created context: ${context.key} with ${entries.length} entries`);
    } catch (error) {
      logError(`Failed to create context ${context.key}: ${error.message}`);
    }
  }

  return createdContexts;
}

async function createEnvironment(token, team) {
  logStep('Creating test environment...');

  const query = new URLSearchParams({ name: ENVIRONMENT_NAME, offset: '0', limit: '1' }).toString();
  const envsData = await apiJson(`/teams/${team.id}/environments?${query}`, { token });
  if (envsData.items.length > 0) {
    const existingEnv = envsData.items[0];
    logSuccess(`Using existing environment: ${existingEnv.name} (ID: ${existingEnv.id})`);
    return existingEnv;
  }

  const created = await apiJson(`/teams/${team.id}/environments`, {
    method: 'POST',
    token,
    body: { name: ENVIRONMENT_NAME, active: true, environmentType: 'Production' },
  });
  logSuccess(`Created environment: ${created.name} (ID: ${created.id})`);
  return created;
}

async function ensureApprovalPolicy(token, teamId) {
  const policies = await apiJson(`/teams/${teamId}/approval-policies`, { token });
  const existing = policies.find((p) => p.name === APPROVAL_POLICY_NAME);
  if (existing) {
    return existing;
  }

  return apiJson(`/teams/${teamId}/approval-policies`, {
    method: 'POST',
    token,
    body: {
      name: APPROVAL_POLICY_NAME,
      description: 'Auto-created policy for performance seeding',
      appliesTo: 'all',
      environmentIds: null,
      requiredApprovers: 1,
      approverRoleIds: [ROLE_IDS.approver],
      approverUserIds: [],
      autoApproveAfterHours: null,
      enabled: true,
    },
  });
}

async function createPipeline(token, team, environment) {
  logStep('Creating pipeline...');

  const query = new URLSearchParams({ name: PIPELINE_NAME, offset: '0', limit: '1' }).toString();
  const pipelinesData = await apiJson(`/teams/${team.id}/pipelines?${query}`, { token });
  if (pipelinesData.items.length > 0) {
    logSuccess(`Using existing pipeline: ${PIPELINE_NAME}`);
    return { id: pipelinesData.items[0].id, environmentId: environment.id };
  }

  const input = {
    name: PIPELINE_NAME,
    stages: [
      {
        environmentId: environment.id,
        orderIndex: 0,
        position: JSON.stringify({ x: 250, y: 250 }),
      },
    ],
    relationships: [],
  };

  const created = await apiJson(`/teams/${team.id}/pipelines`, {
    method: 'POST',
    token,
    body: input,
  });
  logSuccess(`Created pipeline: ${created.name} (ID: ${created.id})`);
  return { id: created.id, environmentId: environment.id };
}

async function deployFeatureStage(token, stageId) {
  let pendingId = null;

  try {
    const request = await apiJson(`/stages/${stageId}/request-change`, {
      method: 'POST',
      token,
      body: { request: 'DEPLOYMENT_REQUESTED' },
    });
    pendingId = request.pendingApprovalRequestId || null;
  } catch (error) {
    if (error.status !== 400) throw error;
  }

  if (pendingId) {
    await apiJson(`/approval-requests/${pendingId}/approve`, {
      method: 'POST',
      token,
      body: { comment: 'Auto-approved by perf seed' },
    });
  }

  try {
    await apiJson(`/stages/${stageId}/request-change`, {
      method: 'POST',
      token,
      body: { request: 'DEPLOYED' },
    });
  } catch (error) {
    if (error.status !== 400) throw error;
  }
}

async function createFeature(token, team, pipeline, index, isContextual = false) {
  const featureType = isContextual ? 'CONTEXTUAL' : 'SIMPLE';

  const variants = isContextual
    ? [
        {
          control: 'control',
          value: false,
          valueType: 'BOOLEAN',
          description: 'Control variant',
        },
        {
          control: 'variant-a',
          value: true,
          valueType: 'BOOLEAN',
          description: 'Variant A',
        },
      ]
    : null;

  const input = {
    key: `feature=${index}`,
    description: `Performance test feature ${index} (${featureType})`,
    featureType,
    enabled: true,
    dependencies: [],
    relationships: [],
    stages: [
      {
        environmentId: pipeline.environmentId,
        orderIndex: 0,
        position: JSON.stringify({ x: 250, y: 250 }),
        bucketingKey: null,
      },
    ],
    variants,
  };

  const feature = await apiJson(`/teams/${team.id}/features`, {
    method: 'POST',
    token,
    body: input,
  });

  const stageId = feature.stages?.[0]?.id;
  return { featureId: feature.id, stageId };
}

async function createFeatures(token, team, pipeline) {
  logStep(`Creating ${TOTAL_FEATURES.toLocaleString()} features...`);
  logStep(`Starting from index: ${START_INDEX}`, true);

  const featureIds = [];
  let errorCount = 0;

  startTime = Date.now();

  for (let i = START_INDEX; i < START_INDEX + TOTAL_FEATURES; i += 1) {
    const isContextual = i >= SIMPLE_FEATURES;

    try {
      const { featureId, stageId } = await createFeature(token, team, pipeline, i, isContextual);
      featureIds.push(featureId);
      createdFeaturesCount += 1;

      if (stageId) {
        await deployFeatureStage(token, stageId);
      }

      if (createdFeaturesCount % Math.max(1, BATCH_SIZE * 10) === 0) {
        logProgress(createdFeaturesCount, TOTAL_FEATURES, `Last: feature=${i}`);
      }
    } catch (error) {
      errorCount += 1;
      logError(`Error creating feature ${i}: ${error.message}`);
      if (errorCount > 10) {
        throw new Error('Too many errors, stopping...');
      }
    }
  }

  return featureIds;
}

async function main() {
  try {
    console.log(`${colors.bright}${colors.blue}FluxGate Performance Test Data (REST)${colors.reset}`);
    logStep(`Target: ${TOTAL_FEATURES.toLocaleString()} features`);
    logStep(`Batch size: ${BATCH_SIZE}`);

    await createAdminIfNeeded();
    let { token, userId } = await loginAsAdmin();
    await assignRolesToAdmin(token, userId);
    // Refresh claims so Requester/Approver roles are present for stage deployment.
    ({ token, userId } = await loginAsAdmin());

    const team = await createPerfTeam(token);
    await createContexts(token, team);
    const environment = await createEnvironment(token, team);
    await ensureApprovalPolicy(token, team.id);
    const pipeline = await createPipeline(token, team, environment);

    await createFeatures(token, team, pipeline);

    console.log('');
    console.log(`${colors.bright}${colors.green}✓ Performance test data created successfully!${colors.reset}`);
    console.log(`${colors.cyan}Summary:${colors.reset}`);
    console.log(`  - Team: ${team.name} (${team.id})`);
    console.log(`  - Environment: ${environment.name} (${environment.id})`);
    console.log(`  - Features: ${createdFeaturesCount}`);
    console.log('');
  } catch (error) {
    logError(`Fatal error: ${error.message}`);
    process.exit(1);
  }
}

main();
