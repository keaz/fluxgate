import http from 'k6/http';
import exec from 'k6/execution';
import { Rate } from 'k6/metrics';

// ============================================================================
// FluxGate Edge Server Breakpoint Test
// ============================================================================
//
// Steps the request rate up (START_RPS, START_RPS + STEP_RPS, ... MAX_RPS) and
// holds each rate for STEP_DURATION. Every step is its own k6 scenario, so
// latency, errors and dropped iterations are measured per step instead of
// cumulatively over the whole run.
//
// A step passes when, for that step alone:
//   p99 latency  <= SLO_P99_MS
//   error rate   <= SLO_ERROR_RATE   (non-200 or an errorCode in the response)
//   dropped iterations <= SLO_DROPPED_RATIO of the planned requests
//
// The breakpoint (max sustainable RPS) is the last step before the first
// failing step. The run stops early once the edge is saturated, i.e. when a
// step exceeds ABORT_P99_MS, ABORT_ERROR_RATE or ABORT_DROPPED_RATIO.
//
// Steady-state test: set START_RPS and MAX_RPS to the same value and
// STEP_DURATION to the hold time, e.g. START_RPS=700 MAX_RPS=700 STEP_DURATION=10m.
//
// Usage:
//   k6 run -e ENVIRONMENT_ID=<env-id> -e TOTAL_FEATURES=1000 breakpoint-test.js
//
//   # With live metrics in the monitoring stack (perf-test/docker-compose.monitoring.yml)
//   K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9095/api/v1/write K6_FEATURES=native-histograms \
//     k6 run -o experimental-prometheus-rw --tag testid=tiny-1000f-breakpoint breakpoint-test.js
//
// Environment variables (defaults in brackets):
//   EDGE_URL            Edge server URL [http://localhost:8081]
//   ENVIRONMENT_ID      Sent as context.environment_id [empty]
//   TOTAL_FEATURES      Number of feature keys to spread requests over [1000]
//   FEATURE_START       Index of the first key, keys are feature=<n> [10000]
//   DISTRIBUTION        uniform | pareto (80% of requests to 20% of keys) [uniform]
//   USERS               Size of the bucketing key pool [10000]
//   START_RPS           First step rate [100]
//   STEP_RPS            Rate increase per step, 0 for a single step [100]
//   MAX_RPS             Last step rate [5000]
//   STEP_DURATION       Hold time per step, e.g. 60s or 2m [60s]
//   WARMUP_DURATION     Unmeasured warm-up at START_RPS, 0s to skip [30s]
//   MAX_VUS             Max concurrent requests per step [500]
//   SLO_P99_MS          [50]
//   SLO_ERROR_RATE      [0.01]
//   SLO_DROPPED_RATIO   [0.01]
//   ABORT_P99_MS        [1000]
//   ABORT_ERROR_RATE    [0.2]
//   ABORT_DROPPED_RATIO [0.05]
//   RESULTS_DIR         Where the summary files are written [results]
//   TEST_NAME           Summary file name prefix [breakpoint]
// ============================================================================

const env = (name, fallback) => (__ENV[name] !== undefined && __ENV[name] !== '' ? __ENV[name] : fallback);
const num = (name, fallback) => {
    const value = Number(env(name, fallback));
    if (Number.isNaN(value)) {
        throw new Error(`${name} must be a number, got "${__ENV[name]}"`);
    }
    return value;
};

function durationSeconds(name, fallback) {
    const value = env(name, fallback);
    const match = /^(\d+)(s|m|h)?$/.exec(value);
    if (!match) {
        throw new Error(`${name} must look like 30s, 2m or 1h, got "${value}"`);
    }
    const unit = { s: 1, m: 60, h: 3600 }[match[2] || 's'];
    return Number(match[1]) * unit;
}

const EDGE_URL = env('EDGE_URL', 'http://localhost:8081').replace(/\/+$/, '');
const ENVIRONMENT_ID = env('ENVIRONMENT_ID', '');
const TOTAL_FEATURES = num('TOTAL_FEATURES', 1000);
const FEATURE_START = num('FEATURE_START', 10000);
const DISTRIBUTION = env('DISTRIBUTION', 'uniform');
const USERS = num('USERS', 10000);

const START_RPS = num('START_RPS', 100);
const STEP_RPS = num('STEP_RPS', 100);
const MAX_RPS = num('MAX_RPS', 5000);
const STEP_SECS = durationSeconds('STEP_DURATION', '60s');
const WARMUP_SECS = durationSeconds('WARMUP_DURATION', '30s');
const MAX_VUS = num('MAX_VUS', 500);

const SLO = {
    p99Ms: num('SLO_P99_MS', 50),
    errorRate: num('SLO_ERROR_RATE', 0.01),
    droppedRatio: num('SLO_DROPPED_RATIO', 0.01),
};
const ABORT = {
    p99Ms: num('ABORT_P99_MS', 1000),
    errorRate: num('ABORT_ERROR_RATE', 0.2),
    droppedRatio: num('ABORT_DROPPED_RATIO', 0.05),
};

const RESULTS_DIR = env('RESULTS_DIR', 'results').replace(/\/+$/, '');
const TEST_NAME = env('TEST_NAME', 'breakpoint');

if (!['uniform', 'pareto'].includes(DISTRIBUTION)) {
    throw new Error(`DISTRIBUTION must be uniform or pareto, got "${DISTRIBUTION}"`);
}

const STEP_RATES = [];
if (STEP_RPS <= 0 || START_RPS >= MAX_RPS) {
    STEP_RATES.push(START_RPS);
} else {
    for (let rate = START_RPS; rate <= MAX_RPS; rate += STEP_RPS) {
        STEP_RATES.push(rate);
    }
}

const stepName = (rate) => `step_${String(rate).padStart(6, '0')}`;
const stepOffsetSecs = (index) => WARMUP_SECS + index * STEP_SECS;

// Response check: the edge answers 200 with an errorCode (e.g. FLAG_NOT_FOUND)
// when it cannot evaluate a flag, so the status alone is not enough.
const evaluationErrors = new Rate('evaluation_errors');

const scenarios = {};
const thresholds = {};

if (WARMUP_SECS > 0) {
    scenarios.warmup = {
        executor: 'constant-arrival-rate',
        rate: START_RPS,
        timeUnit: '1s',
        duration: `${WARMUP_SECS}s`,
        preAllocatedVUs: Math.min(MAX_VUS, Math.max(5, Math.ceil(START_RPS / 100))),
        maxVUs: MAX_VUS,
        gracefulStop: '2s',
    };
}

STEP_RATES.forEach((rate, index) => {
    const name = stepName(rate);
    const tag = `{scenario:${name}}`;
    const planned = rate * STEP_SECS;

    scenarios[name] = {
        executor: 'constant-arrival-rate',
        rate,
        timeUnit: '1s',
        duration: `${STEP_SECS}s`,
        startTime: `${stepOffsetSecs(index)}s`,
        preAllocatedVUs: Math.min(MAX_VUS, Math.max(5, Math.ceil(rate / 100))),
        maxVUs: MAX_VUS,
        gracefulStop: '2s',
    };

    // The always-true thresholds only make k6 keep per-step submetrics for the
    // summary. The SLO verdict is computed in handleSummary; the abort
    // thresholds end the run once the edge is saturated.
    thresholds[`http_reqs${tag}`] = ['count>=0'];
    thresholds[`http_req_duration${tag}`] = [
        'max>=0',
        { threshold: `p(99)<${ABORT.p99Ms}`, abortOnFail: true, delayAbortEval: '5s' },
    ];
    thresholds[`evaluation_errors${tag}`] = [
        'rate>=0',
        { threshold: `rate<${ABORT.errorRate}`, abortOnFail: true, delayAbortEval: '5s' },
    ];
    thresholds[`dropped_iterations${tag}`] = [
        { threshold: `count<${Math.max(1, Math.ceil(planned * ABORT.droppedRatio))}`, abortOnFail: true },
    ];
});

export const options = {
    scenarios,
    thresholds,
    summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'p(99.9)', 'max'],
    systemTags: ['status', 'method', 'scenario', 'expected_response', 'error_code'],
    setupTimeout: '30s',
};

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
const CONTEXT_KEYS = Object.keys(CONTEXT_VALUES);
const HOT_FEATURES = Math.max(1, Math.floor(TOTAL_FEATURES * 0.2));

const randomInt = (max) => Math.floor(Math.random() * max);

function featureIndex() {
    if (DISTRIBUTION === 'uniform' || TOTAL_FEATURES === HOT_FEATURES) {
        return randomInt(TOTAL_FEATURES);
    }
    return Math.random() < 0.8
        ? randomInt(HOT_FEATURES)
        : HOT_FEATURES + randomInt(TOTAL_FEATURES - HOT_FEATURES);
}

function evaluate(flagKey, bucketingKey) {
    const context = { bucketingKey };
    if (ENVIRONMENT_ID) {
        context.environment_id = ENVIRONMENT_ID;
    }
    for (const key of CONTEXT_KEYS) {
        const values = CONTEXT_VALUES[key];
        context[key] = values[randomInt(values.length)];
    }
    return http.post(`${EDGE_URL}/evaluate`, JSON.stringify({ flagKey, context }), {
        headers: { 'Content-Type': 'application/json' },
    });
}

const isEvaluationError = (res) =>
    res.status !== 200 || typeof res.body !== 'string' || /"errorCode":"/.test(res.body);

export function setup() {
    const probeKey = `feature=${FEATURE_START}`;
    const res = evaluate(probeKey, 'setup-probe');
    if (isEvaluationError(res)) {
        exec.test.abort(
            `Probe evaluation of ${probeKey} failed (HTTP ${res.status}): ${String(res.body).slice(0, 200)}. ` +
            'Check EDGE_URL, FEATURE_START and that the test data is populated and deployed.',
        );
    }
    return { startedAtMs: Date.now() };
}

export default function () {
    const flagKey = `feature=${FEATURE_START + featureIndex()}`;
    const res = evaluate(flagKey, `user-${randomInt(USERS)}`);
    evaluationErrors.add(isEvaluationError(res));
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

const round = (value, digits = 2) =>
    value === undefined || value === null || Number.isNaN(value) ? null : Number(value.toFixed(digits));

function stepResult(data, rate, index, lastStepWithData, startedAtMs) {
    const tag = `{scenario:${stepName(rate)}}`;
    const metric = (name) => data.metrics[`${name}${tag}`]?.values || {};
    const duration = metric('http_req_duration');
    const requests = metric('http_reqs').count || 0;
    const dropped = metric('dropped_iterations').count || 0;
    const errorRate = metric('evaluation_errors').rate || 0;
    const planned = rate * STEP_SECS;
    const offset = stepOffsetSecs(index);
    const plannedEndMs = startedAtMs + (offset + STEP_SECS) * 1000;
    // An aborted run ends before the planned end of its last step
    const endMs = startedAtMs ? Math.min(plannedEndMs, Date.now()) : null;
    const elapsedSecs = startedAtMs ? Math.max(1, (endMs - (startedAtMs + offset * 1000)) / 1000) : STEP_SECS;

    const failures = [];
    if (requests === 0) {
        failures.push('not run');
    } else {
        if (duration['p(99)'] > SLO.p99Ms) failures.push(`p99 ${round(duration['p(99)'])}ms > ${SLO.p99Ms}ms`);
        if (errorRate > SLO.errorRate) failures.push(`errors ${round(errorRate * 100, 3)}% > ${SLO.errorRate * 100}%`);
        if (dropped > planned * SLO.droppedRatio) failures.push(`dropped ${dropped} > ${round(planned * SLO.droppedRatio, 0)}`);
        if (index === lastStepWithData && index < STEP_RATES.length - 1) failures.push('run aborted during step');
    }

    return {
        targetRps: rate,
        startedAt: startedAtMs ? new Date(startedAtMs + offset * 1000).toISOString() : null,
        endedAt: startedAtMs ? new Date(endMs).toISOString() : null,
        durationSecs: round(elapsedSecs, 1),
        requests,
        achievedRps: round(requests / Math.min(STEP_SECS, elapsedSecs)),
        dropped,
        errorRate: round(errorRate, 5),
        latencyMs: {
            avg: round(duration.avg, 3),
            min: round(duration.min, 3),
            p50: round(duration.med, 3),
            p90: round(duration['p(90)'], 3),
            p95: round(duration['p(95)'], 3),
            p99: round(duration['p(99)'], 3),
            p999: round(duration['p(99.9)'], 3),
            max: round(duration.max, 3),
        },
        passed: failures.length === 0,
        failures,
    };
}

function markdownReport(result) {
    const rows = result.steps
        .filter((step) => step.requests > 0)
        .map((step) => {
            const l = step.latencyMs;
            const verdict = step.passed ? 'pass' : `FAIL (${step.failures.join('; ')})`;
            return `| ${step.targetRps} | ${step.achievedRps} | ${l.p50} | ${l.p95} | ${l.p99} | ${l.p999} | ${l.max} | ${round(step.errorRate * 100, 3)} | ${step.dropped} | ${verdict} |`;
        });
    const breaking = result.breakingStep
        ? `${result.breakingStep.targetRps} RPS (${result.breakingStep.failures.join('; ')})`
        : 'not reached';
    return [
        `# ${TEST_NAME}`,
        '',
        `- Max sustainable RPS: **${result.maxSustainableRps ?? 'none (first step failed)'}**`,
        `- Breaking step: ${breaking}`,
        `- Peak achieved RPS: ${result.peakAchievedRps}`,
        `- SLO: p99 <= ${SLO.p99Ms}ms, errors <= ${SLO.errorRate * 100}%, dropped <= ${SLO.droppedRatio * 100}%`,
        `- Steps: ${START_RPS} to ${MAX_RPS} RPS by ${STEP_RPS}, ${STEP_SECS}s each, ${WARMUP_SECS}s warm-up`,
        `- Features: ${TOTAL_FEATURES} (${DISTRIBUTION}), users: ${USERS}`,
        '',
        '| Target RPS | Achieved RPS | p50 ms | p95 ms | p99 ms | p99.9 ms | max ms | Errors % | Dropped | Verdict |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|',
        ...rows,
        '',
    ].join('\n');
}

export function handleSummary(data) {
    const startedAtMs = data.setup_data?.startedAtMs;
    let lastStepWithData = -1;
    STEP_RATES.forEach((rate, index) => {
        if ((data.metrics[`http_reqs{scenario:${stepName(rate)}}`]?.values?.count || 0) > 0) {
            lastStepWithData = index;
        }
    });

    const steps = STEP_RATES.map((rate, index) => stepResult(data, rate, index, lastStepWithData, startedAtMs));
    const firstFailure = steps.findIndex((step) => !step.passed);
    const maxSustainable = firstFailure === -1 ? steps[steps.length - 1] : steps[firstFailure - 1];

    const result = {
        meta: {
            testName: TEST_NAME,
            edgeUrl: EDGE_URL,
            environmentId: ENVIRONMENT_ID,
            totalFeatures: TOTAL_FEATURES,
            featureStart: FEATURE_START,
            distribution: DISTRIBUTION,
            users: USERS,
            startRps: START_RPS,
            stepRps: STEP_RPS,
            maxRps: MAX_RPS,
            stepSeconds: STEP_SECS,
            warmupSeconds: WARMUP_SECS,
            maxVus: MAX_VUS,
            slo: SLO,
            abort: ABORT,
            startedAt: startedAtMs ? new Date(startedAtMs).toISOString() : null,
            generatedAt: new Date().toISOString(),
        },
        maxSustainableRps: maxSustainable ? maxSustainable.targetRps : null,
        breakingStep: firstFailure === -1 ? null : steps[firstFailure],
        peakAchievedRps: Math.max(0, ...steps.map((step) => step.achievedRps || 0)),
        steps: steps.filter((step) => step.requests > 0),
    };

    const report = markdownReport(result);
    return {
        stdout: `\n${report}\n`,
        [`${RESULTS_DIR}/${TEST_NAME}.json`]: JSON.stringify(result, null, 2),
        [`${RESULTS_DIR}/${TEST_NAME}.md`]: report,
        [`${RESULTS_DIR}/${TEST_NAME}-k6-summary.json`]: JSON.stringify(data, null, 2),
    };
}
