#!/usr/bin/env node

/**
 * FluxGate Feature Evaluation Script (no Docker)
 *
 * Sends evaluation requests to a locally running edge server, the same way
 * run-perf-tests.sh seeds evaluations, so evaluation analytics show up in the UI.
 * No results are captured; a short summary is printed to the console.
 *
 * The edge server evaluates deterministically, so results only vary when the
 * feature stages carry targeting criteria. Before evaluating, the script reads
 * each feature's type and variants and gives every stage without criteria a
 * randomized set (existing criteria are left untouched):
 *   SIMPLE      one rule on a random context key matching about half of its
 *               values, so each request returns true or false at random
 *   CONTEXTUAL  a rule on a single context value that returns one specific
 *               variant, then a catch-all weighted split over all variants,
 *               so requests return the feature's different variants
 * Every request sends random values of the team's contexts, so the rules match
 * for some users and not for others.
 *
 * Usage:
 *   node evaluate-features.js [--features=1000] [--evals=10] [--users=200]
 *                             [--concurrency=16] [--source=api|range] [--start=0]
 *                             [--team="Performance Test Team"] [--wait=15] [--no-setup]
 *
 * Options:
 *   --features     Max number of features to evaluate (default: 1000)
 *   --evals        Evaluations per feature (default: 10)
 *   --users        Size of the bucketing key pool, i.e. distinct users (default: 200)
 *   --concurrency  Parallel requests to the edge server (default: 16)
 *   --source       api   = fetch feature keys of the team from the backend (default)
 *                  range = generate keys feature=<start> .. feature=<start+features-1>
 *   --start        Start index for --source=range (default: 0)
 *   --team         Team whose features are evaluated (default: Performance Test Team)
 *   --wait         Seconds to wait for the edge server to flush events (default: 15)
 *   --no-setup     Do not add criteria to stages; evaluate the features as they are
 *                  (criteria setup needs --source=api, it is skipped for range)
 *
 * Environment variables:
 *   EDGE_URL        Edge server URL (default: http://localhost:8081)
 *   REST_HTTP_URL   Backend REST URL (default: http://localhost:8080/api/v1)
 *   ADMIN_PASSWORD  Admin password (default: password123)
 *   ENVIRONMENT_ID  Optional. Sent as context.environment_id; must match the edge client's environment
 */

const EDGE_URL = (process.env.EDGE_URL || 'http://localhost:8081').replace(/\/+$/, '');
const API_BASE = (process.env.REST_HTTP_URL
  || process.env.API_BASE_URL
  || 'http://localhost:8080/api/v1').replace(/\/+$/, '');
const DEFAULT_PASSWORD = process.env.ADMIN_PASSWORD || 'password123';
const ENVIRONMENT_ID = process.env.ENVIRONMENT_ID || '';

// Parse command line arguments
const args = process.argv.slice(2);
const argValue = (name, fallback) => {
  const prefix = `--${name}=`;
  const found = args.find((a) => a.startsWith(prefix));
  return found ? found.slice(prefix.length) : fallback;
};

const MAX_FEATURES = parseInt(argValue('features', '1000'), 10);
const EVALS_PER_FEATURE = parseInt(argValue('evals', '10'), 10);
const USER_POOL = parseInt(argValue('users', '200'), 10);
const CONCURRENCY = parseInt(argValue('concurrency', '16'), 10);
const SOURCE = argValue('source', 'api');
const START_INDEX = parseInt(argValue('start', '0'), 10);
const TEAM_NAME = argValue('team', 'Performance Test Team');
const FLUSH_WAIT_SECS = parseInt(argValue('wait', '15'), 10);
const SETUP_CRITERIA = !args.includes('--no-setup');

// Seconds to let the edge server receive criteria changes before evaluating
const CRITERIA_SETTLE_SECS = 3;

// Fallback context values, matching the contexts created by populate-data.js.
// The team's own contexts from the backend are used when they can be loaded.
const CONTEXT_VALUES = {
  region: ['us-east', 'us-west', 'eu-west', 'eu-central', 'ap-south', 'ap-northeast', 'sa-east'],
  tier: ['free', 'basic', 'pro', 'enterprise'],
  userRole: ['viewer', 'editor', 'admin', 'owner'],
  deviceType: ['mobile', 'tablet', 'desktop', 'tv'],
  osType: ['ios', 'android', 'windows', 'macos', 'linux'],
  appVersion: ['v1.0', 'v1.1', 'v1.2', 'v2.0', 'v2.1'],
  language: ['en', 'es', 'fr', 'de', 'ja', 'zh', 'pt', 'ru'],
  country: ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR'],
  beta: ['true', 'false'],
};

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

async function apiJson(pathValue, { method = 'GET', body, token } = {}) {
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

async function loginAsAdmin() {
  const data = await apiJson('/auth/login', {
    method: 'POST',
    body: { username: 'admin', password: DEFAULT_PASSWORD },
  });
  return data.token;
}

async function findTeam(token) {
  const teams = await apiJson('/teams', { token });
  const team = teams.find((t) => t.name === TEAM_NAME);
  if (!team) {
    throw new Error(`Team '${TEAM_NAME}' not found. Run populate-data.js first or pass --team=<name>.`);
  }
  return team;
}

// Runs fn over items with at most `limit` calls in flight
async function runPool(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next;
      next += 1;
      results[index] = await fn(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, worker));
  return results;
}

async function fetchTeamFeatures(token, teamId) {
  const pageSize = 500;
  const features = [];
  let offset = 0;

  while (features.length < MAX_FEATURES) {
    const query = new URLSearchParams({ offset: String(offset), limit: String(pageSize) }).toString();
    const page = await apiJson(`/teams/${teamId}/features?${query}`, { token });
    const items = page.items || [];
    features.push(...items.map((f) => ({ id: f.id, key: f.key, type: f.featureType })));
    offset += items.length;
    if (items.length === 0 || offset >= (page.meta?.total ?? 0)) break;
  }

  return features.slice(0, MAX_FEATURES);
}

// The feature list omits stages and variants, so each feature is loaded on its own
async function loadFeatureDetails(token, features) {
  return runPool(features, CONCURRENCY, async (feature) => {
    const data = await apiJson(`/features/${feature.id}`, { token });
    return {
      ...feature,
      type: data.featureType || feature.type,
      stages: (data.stages || []).map((s) => ({ id: s.id, environmentId: s.environment?.id })),
      variants: (data.variants || []).map((v) => ({ control: v.control, value: v.value })),
    };
  });
}

function generateRangeFeatures() {
  return Array.from({ length: MAX_FEATURES }, (_, i) => ({ key: `feature=${START_INDEX + i}`, type: null }));
}

async function fetchContextValues(token, teamId) {
  const data = await apiJson(`/teams/${teamId}/contexts?limit=500`, { token });
  const items = Array.isArray(data) ? data : data.items || [];
  const values = {};
  for (const context of items) {
    const entries = (context.entries || []).map((e) => e.value);
    if (entries.length > 0) {
      values[context.key] = entries;
    }
  }
  return values;
}

const pick = (values) => values[Math.floor(Math.random() * values.length)];

function shuffle(values) {
  const copy = [...values];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function inRule(contextKey, values) {
  return {
    logicOperator: 'AND',
    conditions: [{ contextKey, operator: 'IN', value: values, orderIndex: 0 }],
  };
}

// Splits 100 evenly over the variants; the remainder goes to the first ones
function evenAllocations(variants) {
  const base = Math.floor(100 / variants.length);
  const remainder = 100 - base * variants.length;
  return variants.map((v, i) => ({ variantControl: v.control, weight: base + (i < remainder ? 1 : 0) }));
}

function buildCriteria(feature, contextValues) {
  const ruleKeys = Object.keys(contextValues).filter((key) => contextValues[key].length >= 2);
  if (ruleKeys.length === 0) {
    throw new Error('No context with at least two values to build rules from');
  }

  if (feature.type === 'CONTEXTUAL' && feature.variants.length > 0) {
    // Users with one specific context value get a fixed variant, everyone else a weighted split
    const targetKey = pick(ruleKeys);
    return [
      {
        priority: 0,
        ruleGroups: [inRule(targetKey, [pick(contextValues[targetKey])])],
        variantSelectionMode: 'SPECIFIC_VARIANT',
        selectedVariantControl: pick(feature.variants).control,
      },
      {
        priority: 1,
        variantSelectionMode: 'WEIGHTED_SPLIT',
        variantAllocations: evenAllocations(feature.variants),
      },
    ];
  }

  // Simple feature (or contextual without variants): about half of the users match
  const key = pick(ruleKeys);
  const values = contextValues[key];
  const matching = shuffle(values).slice(0, Math.max(1, Math.round(values.length / 2)));
  return [{ priority: 0, ruleGroups: [inRule(key, matching)] }];
}

async function setupCriteria(token, features, contextValues) {
  const stats = { configured: 0, kept: 0, failed: 0 };
  const stageTasks = [];
  for (const feature of features) {
    for (const stage of feature.stages) {
      if (!ENVIRONMENT_ID || stage.environmentId === ENVIRONMENT_ID) {
        stageTasks.push({ feature, stage });
      }
    }
  }

  await runPool(stageTasks, CONCURRENCY, async ({ feature, stage }) => {
    try {
      const existing = await apiJson(`/stages/${stage.id}/criteria`, { token });
      if (Array.isArray(existing) && existing.length > 0) {
        stats.kept += 1;
        return;
      }
      await apiJson(`/stages/${stage.id}/criteria`, {
        method: 'PUT',
        token,
        body: buildCriteria(feature, contextValues),
      });
      stats.configured += 1;
    } catch (error) {
      stats.failed += 1;
      if (stats.failed <= 3) {
        logError(`Criteria setup failed for ${feature.key} (stage ${stage.id}): ${error.message}`);
      }
    }
  });

  return stats;
}

function buildContext(contextValues) {
  const context = { bucketingKey: `user-${Math.floor(Math.random() * USER_POOL)}` };
  if (ENVIRONMENT_ID) {
    context.environment_id = ENVIRONMENT_ID;
  }
  for (const [key, values] of Object.entries(contextValues)) {
    context[key] = pick(values);
  }
  return context;
}

async function checkEdge() {
  try {
    const response = await fetch(`${EDGE_URL}/health`);
    if (response.ok) {
      logSuccess(`Edge server reachable: ${EDGE_URL}`);
    } else {
      // /health reports the backend stream state; /evaluate can still work
      logWarning(`Edge /health returned ${response.status} (stream to backend not connected); continuing`);
    }
  } catch (error) {
    throw new Error(`Edge server not reachable at ${EDGE_URL}: ${error.message}`);
  }
}

async function evaluateAll(features, contextValues) {
  const tasks = [];
  for (const feature of features) {
    for (let i = 0; i < EVALS_PER_FEATURE; i += 1) {
      tasks.push(feature);
    }
  }

  const stats = { total: tasks.length, ok: 0, failed: 0, byOutcome: {}, byType: {}, firstErrors: [] };
  let next = 0;
  let done = 0;
  const startTime = Date.now();

  const record = (outcome) => {
    stats.byOutcome[outcome] = (stats.byOutcome[outcome] || 0) + 1;
  };

  // Counts what each feature type resolved to: true/false for simple, the variant for contextual
  const recordResult = (type, data) => {
    const result = data.variant
      ? `variant ${data.variant} = ${JSON.stringify(data.value)}`
      : String(data.value);
    const bucket = (stats.byType[type || 'UNKNOWN TYPE'] ||= {});
    bucket[result] = (bucket[result] || 0) + 1;
  };

  async function worker() {
    while (next < tasks.length) {
      const { key: flagKey, type } = tasks[next];
      next += 1;

      try {
        const response = await fetch(`${EDGE_URL}/evaluate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ flagKey, context: buildContext(contextValues) }),
        });

        if (response.ok) {
          const data = await response.json();
          stats.ok += 1;
          record(data.errorCode ? `${data.reason} (${data.errorCode})` : data.reason);
          recordResult(type, data);
        } else {
          const text = await response.text().catch(() => '');
          stats.failed += 1;
          record(`HTTP ${response.status}`);
          if (stats.firstErrors.length < 3) {
            stats.firstErrors.push(`${flagKey}: HTTP ${response.status} ${text}`.trim());
          }
        }
      } catch (error) {
        stats.failed += 1;
        record('NETWORK_ERROR');
        if (stats.firstErrors.length < 3) {
          stats.firstErrors.push(`${flagKey}: ${error.message}`);
        }
      }

      done += 1;
      if (done % 1000 === 0 || done === tasks.length) {
        const elapsed = (Date.now() - startTime) / 1000;
        console.log(
          `${colors.magenta}Progress: ${done}/${tasks.length} | ${(done / (elapsed || 1)).toFixed(1)} req/sec | ${elapsed.toFixed(1)}s elapsed${colors.reset}`
        );
      }
    }
  }

  await Promise.all(Array.from({ length: Math.max(1, CONCURRENCY) }, worker));
  return stats;
}

function printStats(stats) {
  console.log('');
  console.log(`${colors.cyan}Edge responses:${colors.reset}`);
  console.log(`  - Requests: ${stats.total} (ok: ${stats.ok}, failed: ${stats.failed})`);
  for (const [outcome, count] of Object.entries(stats.byOutcome).sort((a, b) => b[1] - a[1])) {
    console.log(`  - ${outcome}: ${count}`);
  }
  for (const [type, results] of Object.entries(stats.byType)) {
    const total = Object.values(results).reduce((sum, count) => sum + count, 0);
    console.log(`${colors.cyan}${type} results:${colors.reset}`);
    for (const [result, count] of Object.entries(results).sort((a, b) => b[1] - a[1])) {
      console.log(`  - ${result}: ${count} (${((count / total) * 100).toFixed(1)}%)`);
    }
  }
  for (const message of stats.firstErrors) {
    logError(message);
  }

  if (stats.byOutcome['DEFAULT (FLAG_NOT_FOUND)']) {
    logWarning('FLAG_NOT_FOUND responses are not recorded as evaluations (unknown key or no stage in the edge client\'s environment)');
  }
  if (stats.byOutcome.DISABLED) {
    logWarning('DISABLED responses are recorded, but always as false: the feature stage is not enabled in this environment');
  }
}

async function main() {
  try {
    console.log(`${colors.bright}${colors.blue}FluxGate Feature Evaluation (no Docker)${colors.reset}`);
    logStep(`Edge URL: ${EDGE_URL}`);
    logStep(`Backend URL: ${API_BASE}`);
    logStep(`Key source: ${SOURCE}${SOURCE === 'range' ? ` (start: ${START_INDEX})` : ` (team: ${TEAM_NAME})`}`);
    logStep(`Evaluations per feature: ${EVALS_PER_FEATURE} | Users: ${USER_POOL} | Concurrency: ${CONCURRENCY}`);
    if (ENVIRONMENT_ID) {
      logStep(`Environment ID: ${ENVIRONMENT_ID}`);
    }

    await checkEdge();

    // The backend login is only needed to list team features and to confirm the result
    let token = null;
    let team = null;
    try {
      token = await loginAsAdmin();
      team = await findTeam(token);
    } catch (error) {
      if (SOURCE === 'api') throw error;
      logWarning(`Backend lookup skipped: ${error.message}`);
    }

    let contextValues = CONTEXT_VALUES;
    if (token && team) {
      try {
        const teamValues = await fetchContextValues(token, team.id);
        if (Object.keys(teamValues).length > 0) {
          contextValues = teamValues;
          logSuccess(`Using ${Object.keys(teamValues).length} team contexts: ${Object.keys(teamValues).join(', ')}`);
        }
      } catch (error) {
        logWarning(`Team contexts not loaded, using built-in values: ${error.message}`);
      }
    }

    logStep('Resolving features...');
    let features;
    if (SOURCE === 'range') {
      features = generateRangeFeatures();
    } else {
      features = await loadFeatureDetails(token, await fetchTeamFeatures(token, team.id));
    }
    if (features.length === 0) {
      throw new Error('No feature keys to evaluate');
    }
    const typeCounts = features.reduce((counts, f) => {
      const type = f.type || 'UNKNOWN TYPE';
      counts[type] = (counts[type] || 0) + 1;
      return counts;
    }, {});
    logSuccess(
      `Evaluating ${features.length} features (${Object.entries(typeCounts).map(([t, n]) => `${t}: ${n}`).join(', ')})`
    );

    if (!SETUP_CRITERIA) {
      logStep('Criteria setup disabled (--no-setup)');
    } else if (SOURCE === 'range') {
      logWarning('Criteria setup skipped: --source=range has no feature types or stages');
    } else {
      logStep('Adding randomized criteria to stages without criteria...');
      const setup = await setupCriteria(token, features, contextValues);
      logSuccess(`Stages configured: ${setup.configured}, kept existing criteria: ${setup.kept}, failed: ${setup.failed}`);
      if (setup.configured > 0) {
        await new Promise((resolve) => setTimeout(resolve, CRITERIA_SETTLE_SECS * 1000));
      }
    }

    const stats = await evaluateAll(features, contextValues);
    printStats(stats);

    if (stats.ok === 0) {
      throw new Error('No successful evaluations');
    }

    if (FLUSH_WAIT_SECS > 0) {
      logStep(`Waiting ${FLUSH_WAIT_SECS}s for the edge server to flush evaluation events...`);
      await new Promise((resolve) => setTimeout(resolve, FLUSH_WAIT_SECS * 1000));
    }

    if (token && team) {
      const query = new URLSearchParams({ period: 'PERIOD_24H', teamId: team.id }).toString();
      const summary = await apiJson(`/metrics/evaluations/summary?${query}`, { token });
      logSuccess(
        `Backend reports ${summary.totalEvaluations} evaluations in the last 24h for '${team.name}' `
        + `(${summary.uniqueUsers} unique users, top feature: ${summary.topFeatureKey ?? 'n/a'})`
      );
    }

    console.log('');
    console.log(`${colors.bright}${colors.green}✓ Done. Open the UI to view evaluation details.${colors.reset}`);
  } catch (error) {
    logError(`Fatal error: ${error.message}`);
    process.exit(1);
  }
}

main();
