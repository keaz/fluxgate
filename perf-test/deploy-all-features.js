#!/usr/bin/env node

/**
 * FluxGate Deploy-All Script (REST)
 *
 * Deploys every feature stage (one stage per environment) of every team, following
 * the same path a user takes in the UI:
 *
 *   NOT_DEPLOYED ──request──▶ DEPLOYMENT_REQUESTED ──approve──▶ DEPLOYMENT_APPROVED ──deploy──▶ DEPLOYED
 *
 * Preparation (idempotent):
 *   - Admin gets the Approver and Requester roles (existing roles are kept).
 *   - Admin becomes a member of each target team (existing memberships are kept).
 *     Approval routing only counts team members with the Approver role.
 *   - Environments that no enabled approval policy covers get an
 *     "Auto Deploy Policy" (1 approver, Approver role). Without a policy a stage
 *     stays in DEPLOYMENT_REQUESTED and can never reach DEPLOYED.
 *
 * Stages are deployed in pipeline order (orderIndex). Stages blocked by feature
 * dependencies are retried in later passes, after their dependencies deploy.
 *
 * Usage:
 *   node deploy-all-features.js [--team="Performance Test Team"] [--env=Perf-Test-Prod]
 *                               [--concurrency=4] [--freeze-override-reason="..."] [--dry-run]
 *
 * Options:
 *   --team                    Only this team (default: all teams)
 *   --env                     Only environments with this name (default: all environments)
 *   --concurrency             Features deployed in parallel (default: 4)
 *   --freeze-override-reason  Reason sent when a change freeze is active
 *   --dry-run                 Print what would be deployed; change nothing
 *
 * Environment variables:
 *   REST_HTTP_URL   Backend REST URL (default: http://localhost:8080/api/v1)
 *   ADMIN_USERNAME  Admin username (default: admin)
 *   ADMIN_PASSWORD  Admin password (default: password123)
 */

const API_BASE = (process.env.REST_HTTP_URL
  || process.env.API_BASE_URL
  || 'http://localhost:8080/api/v1').replace(/\/+$/, '');
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'password123';

// Parse command line arguments
const args = process.argv.slice(2);
const argValue = (name, fallback) => {
  const prefix = `--${name}=`;
  const found = args.find((a) => a.startsWith(prefix));
  return found ? found.slice(prefix.length) : fallback;
};

const TEAM_FILTER = argValue('team', null);
const ENV_FILTER = argValue('env', null);
const CONCURRENCY = parseInt(argValue('concurrency', '4'), 10);
const FREEZE_OVERRIDE_REASON = argValue('freeze-override-reason', null);
const DRY_RUN = args.includes('--dry-run');

const ROLE_IDS = {
  approver: '00000000-0000-0000-0000-000000000001',
  requester: '00000000-0000-0000-0000-000000000002',
};

const AUTO_POLICY_NAME = 'Auto Deploy Policy';
const APPROVAL_COMMENT = 'Auto-approved by deploy-all-features.js';
const PAGE_SIZE = 200;
const MAX_PASSES = 5;

// Stage statuses from which a new deployment can be requested
const REQUESTABLE_STATUSES = new Set(['NOT_DEPLOYED', 'DEPLOYMENT_REJECTED', 'ROLLBACKED']);
// A rollback is in progress or was rejected; deploying is not a valid transition
const ROLLBACK_STATUSES = new Set(['ROLLBACK_REQUESTED', 'ROLLBACK_APPROVED', 'ROLLBACK_REJECTED']);

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

function logStep(message, isSubstep = false) {
  const prefix = isSubstep ? '  →' : '▶';
  console.log(`${colors.cyan}${prefix} ${message}${colors.reset}`);
}

function logSuccess(message) {
  console.log(`${colors.green}✓ ${message}${colors.reset}`);
}

function logWarning(message) {
  console.log(`${colors.yellow}⚠ ${message}${colors.reset}`);
}

function logError(message) {
  console.error(`${colors.red}✗ ${message}${colors.reset}`);
}

let token = null;

async function apiJson(pathValue, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${pathValue}`, {
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

async function fetchAllPages(pathValue, extraParams = {}) {
  const items = [];
  let offset = 0;
  for (;;) {
    const query = new URLSearchParams({ ...extraParams, offset: String(offset), limit: String(PAGE_SIZE) });
    const page = await apiJson(`${pathValue}?${query}`);
    const pageItems = page.items || [];
    items.push(...pageItems);
    offset += pageItems.length;
    if (pageItems.length === 0 || offset >= (page.meta?.total ?? 0)) break;
  }
  return items;
}

async function login() {
  const data = await apiJson('/auth/login', {
    method: 'POST',
    body: { username: ADMIN_USERNAME, password: ADMIN_PASSWORD },
  });
  token = data.token;
  return data.user;
}

// Role assignment replaces all roles, so merge with the current ones
async function ensureAdminRoles(userId) {
  const current = await apiJson(`/users/${userId}/roles`);
  const currentIds = current.map((r) => r.id);
  const required = [ROLE_IDS.approver, ROLE_IDS.requester];
  if (required.every((id) => currentIds.includes(id))) {
    logSuccess(`Admin roles OK: ${current.map((r) => r.name).join(', ')}`);
    return false;
  }
  if (DRY_RUN) {
    logStep('[dry-run] Would add Approver and Requester roles to admin', true);
    return false;
  }
  const roles = await apiJson(`/users/${userId}/roles`, {
    method: 'POST',
    body: { roleIds: [...new Set([...currentIds, ...required])] },
  });
  logSuccess(`Admin roles set: ${roles.map((r) => r.name).join(', ')}`);
  return true;
}

// Team assignment replaces all memberships, so merge with the current ones
async function ensureAdminTeams(userId, teams) {
  const user = await apiJson(`/users/${userId}`);
  const currentIds = user.teamIds || [];
  const missing = teams.filter((t) => !currentIds.includes(t.id));
  if (missing.length === 0) {
    logSuccess('Admin is a member of all target teams');
    return;
  }
  const names = missing.map((t) => t.name).join(', ');
  if (DRY_RUN) {
    logStep(`[dry-run] Would add admin to teams: ${names}`, true);
    return;
  }
  await apiJson(`/users/${userId}/teams`, {
    method: 'POST',
    body: { teamIds: [...new Set([...currentIds, ...missing.map((t) => t.id)])] },
  });
  logSuccess(`Added admin to teams: ${names}`);
}

// Mirrors policy_applies() in the backend approval logic
function policyApplies(policy, env) {
  if (!policy.enabled) return false;
  switch (policy.appliesTo) {
    case 'all':
      return true;
    case 'production_only':
      return (env.environmentType || '').toLowerCase() === 'production';
    case 'specific_environments':
      return (policy.environmentIds || []).includes(env.id);
    default:
      return false;
  }
}

async function ensureApprovalPolicies(team, environments) {
  const policies = await apiJson(`/teams/${team.id}/approval-policies`);
  const uncovered = environments.filter((env) => !policies.some((p) => policyApplies(p, env)));
  if (uncovered.length === 0) {
    logSuccess(`[${team.name}] Approval policies cover all environments`);
    return;
  }

  const names = uncovered.map((e) => e.name).join(', ');
  if (DRY_RUN) {
    logStep(`[dry-run] [${team.name}] Would create '${AUTO_POLICY_NAME}' for: ${names}`, true);
    return;
  }

  const existing = policies.find((p) => p.name === AUTO_POLICY_NAME && p.appliesTo === 'specific_environments');
  if (existing) {
    await apiJson(`/approval-policies/${existing.id}`, {
      method: 'PATCH',
      body: {
        enabled: true,
        environmentIds: [...new Set([...(existing.environmentIds || []), ...uncovered.map((e) => e.id)])],
      },
    });
    logSuccess(`[${team.name}] Extended '${AUTO_POLICY_NAME}' to: ${names}`);
    return;
  }

  await apiJson(`/teams/${team.id}/approval-policies`, {
    method: 'POST',
    body: {
      name: AUTO_POLICY_NAME,
      description: 'Created by deploy-all-features.js for environments without an approval policy',
      appliesTo: 'specific_environments',
      environmentIds: uncovered.map((e) => e.id),
      requiredApprovers: 1,
      approverRoleIds: [ROLE_IDS.approver],
      approverUserIds: [],
      autoApproveAfterHours: null,
      enabled: true,
    },
  });
  logSuccess(`[${team.name}] Created '${AUTO_POLICY_NAME}' for: ${names}`);
}

// Pending approval requests per team, keyed by stage id (for stages already in DEPLOYMENT_REQUESTED)
const pendingRequestCache = new Map();

async function findPendingDeployRequest(teamId, stageId) {
  if (!pendingRequestCache.has(teamId)) {
    const requests = await fetchAllPages(`/teams/${teamId}/approval-requests`, { statuses: 'pending' });
    const byStage = new Map();
    for (const request of requests) {
      const payload = request.changePayload || {};
      if (payload.stage_id && payload.next_status === 'DEPLOYMENT_REQUESTED') {
        byStage.set(payload.stage_id, request.id);
      }
    }
    pendingRequestCache.set(teamId, byStage);
  }
  return pendingRequestCache.get(teamId).get(stageId) || null;
}

async function requestStageChange(stageId, request) {
  const body = { request };
  if (FREEZE_OVERRIDE_REASON) {
    body.freezeOverrideReason = FREEZE_OVERRIDE_REASON;
  }
  return apiJson(`/stages/${stageId}/request-change`, { method: 'POST', body });
}

async function getStageStatus(featureId, stageId) {
  const feature = await apiJson(`/features/${featureId}`);
  return feature.stages?.find((s) => s.id === stageId)?.status;
}

async function approve(requestId) {
  const request = await apiJson(`/approval-requests/${requestId}/approve`, {
    method: 'POST',
    body: { comment: APPROVAL_COMMENT },
  });
  if (request.status === 'pending') {
    throw new Error(
      `Approval request ${requestId} still pending (${request.approvedCount}/${request.policy?.requiredApprovers ?? '?'} approvals); `
      + 'the policy needs more approvers than the admin alone'
    );
  }
  if (request.status !== 'approved' && request.status !== 'auto_approved') {
    throw new Error(`Approval request ${requestId} ended as '${request.status}'`);
  }
}

/**
 * Moves one stage to DEPLOYED. Returns 'deployed' or 'already', throws on failure.
 */
async function deployStage(team, feature, stage) {
  let status = stage.status;

  if (status === 'DEPLOYED') return 'already';
  if (ROLLBACK_STATUSES.has(status)) {
    throw new Error(`stage is in ${status}; finish or reject the rollback first`);
  }
  if (DRY_RUN) return 'deployed';

  if (REQUESTABLE_STATUSES.has(status)) {
    const result = await requestStageChange(stage.id, 'DEPLOYMENT_REQUESTED');
    if (result.pendingApprovalRequestId) {
      await approve(result.pendingApprovalRequestId);
    }
    status = await getStageStatus(feature.id, stage.id);
  }

  if (status === 'DEPLOYMENT_REQUESTED') {
    const requestId = await findPendingDeployRequest(team.id, stage.id);
    if (!requestId) {
      throw new Error('stage is DEPLOYMENT_REQUESTED but has no pending approval request (no applicable policy?)');
    }
    await approve(requestId);
    status = await getStageStatus(feature.id, stage.id);
  }

  if (status !== 'DEPLOYMENT_APPROVED') {
    throw new Error(`expected DEPLOYMENT_APPROVED after approval, got ${status}`);
  }

  await requestStageChange(stage.id, 'DEPLOYED');
  return 'deployed';
}

async function runPool(items, worker) {
  let next = 0;
  async function run() {
    while (next < items.length) {
      const item = items[next];
      next += 1;
      await worker(item);
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, CONCURRENCY) }, run));
}

/**
 * Deploys all stages of one feature in pipeline order. Stops at the first
 * failing stage so later environments never get ahead of earlier ones.
 */
async function deployFeature(team, featureId, envIds, stats) {
  const feature = await apiJson(`/features/${featureId}`);
  const stages = (feature.stages || [])
    .filter((s) => envIds.has(s.environment?.id))
    .sort((a, b) => a.orderIndex - b.orderIndex);

  if (stages.length === 0) {
    stats.noStages += 1;
    return null;
  }

  for (const stage of stages) {
    const envName = stage.environment?.name || stage.environment?.id;
    try {
      const outcome = await deployStage(team, feature, stage);
      if (outcome === 'already') {
        stats.already += 1;
      } else {
        stats.deployed += 1;
        if (DRY_RUN) {
          logStep(`[dry-run] ${feature.key} → ${envName} (${stage.status})`, true);
        }
      }
    } catch (error) {
      return { feature, envName, message: error.message };
    }
  }
  return null;
}

async function deployTeam(team, stats) {
  const allEnvironments = await fetchAllPages(`/teams/${team.id}/environments`);
  const environments = allEnvironments.filter((e) => !ENV_FILTER || e.name === ENV_FILTER);
  if (environments.length === 0) {
    logWarning(`[${team.name}] No matching environments, skipping`);
    return;
  }
  logStep(`[${team.name}] Environments: ${environments.map((e) => e.name).join(', ')}`);

  await ensureApprovalPolicies(team, environments);

  const features = await fetchAllPages(`/teams/${team.id}/features`);
  logStep(`[${team.name}] Deploying ${features.length} features...`);

  const envIds = new Set(environments.map((e) => e.id));
  let pending = features.map((f) => f.id);
  let failures = [];

  // Later passes retry features whose stages were blocked, e.g. by a dependency
  // that deployed in the meantime. Stop when a pass makes no progress.
  for (let pass = 1; pass <= MAX_PASSES && pending.length > 0; pass += 1) {
    const deployedBefore = stats.deployed;
    failures = [];

    await runPool(pending, async (featureId) => {
      try {
        const failure = await deployFeature(team, featureId, envIds, stats);
        if (failure) failures.push(failure);
      } catch (error) {
        failures.push({ feature: { id: featureId, key: featureId }, envName: '-', message: error.message });
      }
    });

    pending = failures.map((f) => f.feature.id);
    if (pending.length > 0 && stats.deployed > deployedBefore && pass < MAX_PASSES) {
      logStep(`[${team.name}] Pass ${pass}: ${pending.length} features blocked, retrying...`, true);
      pendingRequestCache.delete(team.id);
    } else {
      break;
    }
  }

  for (const failure of failures) {
    stats.failed += 1;
    logError(`[${team.name}] ${failure.feature.key} → ${failure.envName}: ${failure.message}`);
  }
}

async function main() {
  try {
    console.log(`${colors.bright}${colors.blue}FluxGate Deploy All Features${DRY_RUN ? ' (dry run)' : ''}${colors.reset}`);
    logStep(`Backend URL: ${API_BASE}`);
    logStep(`Team: ${TEAM_FILTER || 'all'} | Environment: ${ENV_FILTER || 'all'} | Concurrency: ${CONCURRENCY}`);

    let user = await login();
    logSuccess(`Logged in as: ${user.username}`);

    const teams = (await apiJson('/teams')).filter((t) => !TEAM_FILTER || t.name === TEAM_FILTER);
    if (teams.length === 0) {
      throw new Error(TEAM_FILTER ? `Team '${TEAM_FILTER}' not found` : 'No teams found');
    }

    if (await ensureAdminRoles(user.id)) {
      // Roles are carried in the JWT, so log in again to pick them up
      user = await login();
    }
    await ensureAdminTeams(user.id, teams);

    const stats = { deployed: 0, already: 0, failed: 0, noStages: 0 };
    const startTime = Date.now();

    for (const team of teams) {
      await deployTeam(team, stats);
    }

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log('');
    console.log(`${colors.cyan}Summary (${elapsed}s):${colors.reset}`);
    console.log(`  - Stages ${DRY_RUN ? 'to deploy' : 'deployed'}: ${stats.deployed}`);
    console.log(`  - Stages already deployed: ${stats.already}`);
    console.log(`  - Features with failed stages: ${stats.failed}`);
    console.log(`  - Features without stages in the target environments: ${stats.noStages}`);

    if (stats.failed > 0) {
      process.exit(1);
    }
  } catch (error) {
    logError(`Fatal error: ${error.message}`);
    process.exit(1);
  }
}

main();
