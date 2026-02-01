# FluxGate System Guide

FluxGate is a closed-source, end-to-end feature flag delivery platform that combines a Rust backend, a Rust edge server, and a React-based administration UI with Spring integration tooling. This guide summarizes the architecture, configuration, API access, Spring library usage, and OpenFeature compatibility so platform operators and integrators can plan deployments, automate configuration, and consume the feature flags without needing to see implementation code.

## Architecture at a Glance

- **Backend service** (feature-toggle) exposes a GraphQL admin surface, gRPC streaming, and diagnostics while persisting everything in PostgreSQL. It also functions as the single source of truth for features, pipelines, criteria, analytics, and kill switch state.
- **Edge server** (feature-edge-server) maintains a long-lived gRPC subscription to the backend for feature updates, evaluates requests from clients against deterministic bucketing + ordered criteria, caches sticky assignments, and flushes analytics/assignments on a schedule.
- **UI** (feature-toggle-ui) is a React + Apollo Client dashboard; it talks to the backend via GraphQL for CRUD, subscriptions, and dashboards.
- **Spring Starter** (fluxgate-spring) lets Java applications talk to the edge server through a familiar Spring Boot configuration and optionally exposes OpenFeature bindings for SDK-based evaluation.

Refer to the existing system diagrams (`media/new_evaluation.jpg` illustrates the evaluation pipeline and `media/system_overview.jpg` shows the control plane/dashboard layout) for a visual overview of the components, data flows, and observability dashboards.

## Delivery Topology and Data Flow

1. The backend stores feature definitions, stages, contexts, criteria, variants, kill switches, and analytics events in PostgreSQL. It publishes feature updates through an internal broadcast channel and serves that data over gRPC to subscribed edge nodes.
2. Each edge node opens a streaming gRPC connection to fetch an initial snapshot of all active features plus incremental feature updates; it keeps that cache in memory for low-latency evaluations.
3. Clients (SDKs, REST callers, OpenFeature consumers) call the edge’s HTTP evaluation endpoint or the OFREP path. The edge resolves the request against cached rules, applies deterministic bucketing by sticky key, evaluates ordered criteria, respects kill switches/rollbacks, and returns the value plus the reason/variant metadata.
4. Evaluation events, sticky assignments, and telemetry are collected locally on the edge and flushed to the backend at configurable intervals, enabling the backend to power the real-time dashboard, analytics, and auditing views.
5. The UI consumes GraphQL queries/mutations for administration and GraphQL subscriptions for live metrics, while also surfacing kill switch status, approval policies, and dependency graphs.

## Configuration Details

### Backend (feature-toggle)
- **DATABASE_URL**: A PostgreSQL DSN (user/password/host/port/database) that the backend uses for persistence and migrations. Migrations live under the feature-toggle backend module.
- **Allowed origins and listen addresses**: Customizable via `config.toml` (e.g., CORS origins, HTTP bind address for GraphQL, gRPC bind address, and the JWT signing secret that should be rotated in production). Log levels are controlled by the bundled `log4rs.yaml` file.
- **Multi-node considerations**: Multiple backend replicas share updates over broadcast channels; ensure gRPC binds and health endpoints are monitored for readiness/liveness.

### Edge (feature-edge-server)
- **EDGE_BACKEND_GRPC**: URL to contact the backend’s gRPC service (default is the local backend but should point to the cluster VIP in production).
- **EDGE_HTTP_ADDR**: HTTP listener for evaluation and health endpoints.
- **EDGE_CLIENT_ID / EDGE_CLIENT_SECRET**: Credentials provisioned in the backend for each consuming application. They gate edge evaluations and are required for both custom REST and OpenFeature evaluation flows.
- **Assignment/Evaluation flush periods**: `EDGE_ASSIGNMENT_FLUSH_SECS` and `EDGE_EVALUATION_FLUSH_SECS` control how often the edge pushes collected sticky assignments or analytics to the backend to power dashboards.
- **Observability**: Edge exposes `/health` for readiness probes and `/docs` for Swagger-based API reference when running locally.

### UI (feature-toggle-ui)
- **Runtime configuration**: The container generates a `config.js` file at startup from env vars such as `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_PROTOCOL`, and `WS_PROTOCOL`. These determine which backend host the UI talks to for GraphQL and WebSocket subscriptions.
- **Dev defaults**: During local development with Vite, the UI targets a local backend at `http://localhost:8080/graphql` unless the runtime config overrides it.

### Spring Boot Starter (fluxgate-spring)
- **Connection properties**: Configure `fluxgate.base-url`, `fluxgate.client-id`, and `fluxgate.client-secret` so the starter can authenticate to the edge server. Timeout, retry, and fallback behavior (connection/read timeout, retry attempts, retry delay/multiplier, fallback value) are adjustable for resilience during edge outages.
- **Metrics and health**: Micrometer metrics and Spring Actuator health indicators can be toggled (`fluxgate.metrics-enabled`, `fluxgate.health-check-enabled`, `fluxgate.health-check-interval`). Caching of evaluations (TTL/size) is optional for reducing edge calls.
- **OpenFeature toggle**: `fluxgate.openfeature.enabled` controls whether the starter binds OpenFeature’s `Client` interface alongside the proprietary `FluxGateClient` API.

### Kubernetes / Container Notes
- A Kubernetes deployment references secrets for `DATABASE_URL`, client credentials, and custom config maps (if overriding `config.toml`). Services expose GraphQL (HTTP), gRPC, and edge HTTP ports; an ingress routes `/graphql`, `/docs`, `/evaluate`, and the UI host. Replace placeholders before applying manifests and adjust resource limits/probes for production workloads.
- Docker Compose examples exist for local quickstarts, wiring up backend, UI, and Postgres with fixed credentials (swap them for secure values before sharing).

## API Surface Overview

### Edge Evaluation Endpoint (`POST /evaluate`)
- Accepts a JSON payload containing a flag identifier plus a context object of attributes such as `bucketingKey`, `environment_id`, and additional targeting keys (user ID, tier, role, etc.).
- Returns the resolved flag key, the evaluated value (boolean, string, number, or JSON object), the variant identifier (if applicable), and an explanation reason (`TARGETED_MATCH`, `DEFAULT`, `DISABLED`, etc.).
- The endpoint powers quick evaluations from custom scripts, internal services, and automated tests.

### OpenFeature Remote Evaluation Protocol (OFREP)
- FluxGate implements the OFREP specification under `POST /ofrep/v1/evaluate/flags/{flagKey}` so any OpenFeature-compliant SDK can call FluxGate as a remote provider.
- The same context fields (environment, bucketing key, user attributes) drive evaluations.
- The response mirrors the OFREP schema with the feature key, resolved value, reason, optional variant ID, and optional metadata for auditing or hooks.
- This standard path makes FluxGate interoperable with OpenFeature clients across languages without embedding FluxGate-specific SDKs.

### GraphQL Admin API
- Backend exposes mutations/queries for managing feature definitions, stages, criteria, variants, approval policies, and kill switches.
- Available operations include creating feature variants, querying features with their variant lists, updating stage criteria with priority and rollouts, and emergency enable/disable of kill switches with optional auto-rollback scheduling.
- Subscriptions provide live evaluation metrics (rates, summary, dashboard data) so the UI can refresh charts every ~30 seconds.
- The GraphQL endpoint runs at `/graphql`, has GraphiQL enabled for manual inspection, and can be secured via JWT-based authentication with RBAC profiles (requester/approver/team admin).

### Real-Time and Observability APIs
- GraphQL subscriptions stream evaluation rates, success/cach hit rates, and dashboard aggregates for time-series insight across environments, features, and clients.
- Edge and backend expose health endpoints for readiness/liveness (backend GraphQL and edge `/health`).
- Analytics flows are batched from edge to backend at configurable intervals, enabling the UI’s dashboards to visualize last 24-hour data, kill switch status, and pipeline metrics.

## Metrics ingestion and analysis

- **Metric definitions** are created through the backend GraphQL mutation `createMetric(teamId, input)` (`feature-toggle-backend/src/graphql/mutation.rs` around the GraphQL schema file). Each metric carries a unique key, descriptive name, optional unit, and a `MetricType` (`Numeric` or `Conversion` as defined in `feature-toggle-backend/src/database/metrics.rs`) plus optional success criteria metadata. The backend enforces key/name validation and ensures duplicates are rejected when `logic::metrics::MetricLogic::create_metric` is invoked. Teams use this mutation to declare KPIs before sending measurement events.
- **Metric events** flow into `feature-toggle-backend/src/logic/metrics.rs`. The logic validates clients via `client_id`/`client_secret`, ensures required fields (`metric_key`, `user_context`) are present, caps conversion metrics between 0.0 and 1.0, and deduplicates conversion totals by benchmarking per-event `user_context`. Valid metric rows are materialized through `CreateMetricEvent`, with variant, feature, and environment IDs carried through to the persistence layer and aggregated by the scheduled `MetricsAggregator` job. The logic returns the count of processed events so the sender can confirm ingestion.
- **Ingestion paths**:
  1. **HTTP endpoint** `POST /metrics/track` (`feature-toggle-backend/src/lib.rs`) accepts the client credentials plus a batch of `MetricEventPayload` entries (metric key, optional feature/environment/variant, numeric value, metadata, timestamp). Timestamp is optional (defaults to `Utc::now`), and environment IDs must be valid UUIDs.
  2. **gRPC method** `FeatureEvaluation::TrackMetrics` (`feature-toggle-backend/src/grpc/mod.rs`) exposes the same contract as the HTTP endpoint, letting edge nodes, SDKs, or automation frameworks push metric events through the gRPC interface.
 3. **Edge server forwarding**: The edge batches evaluation counts/assignments and forwards them to the backend using the gRPC track metrics contract so dashboards stay current.
- **Querying aggregated metrics** is available via GraphQL queries (`metrics`, `metricsByFeature`, `experimentAnalysis`) which rely on pre-aggregated data stored by the backend after `MetricsAggregator` runs hourly/daily buckets. This enables the UI’s experiment analysis charts and time-series MetricResult rows (time buckets, conversion rates, mean values, variance, and confidence intervals).

## Spring Integration & OpenFeature Compatibility

- The Spring Boot starter auto-configures its `FluxGateClient` to call the edge evaluation endpoint, wrapping retries, timeouts, cache controls, and fallback behavior. You can inject the client into controllers or services for blocking or asynchronous evaluations (via non-blocking `CompletableFuture` support backed by the starter). Health and metrics tie into Spring Boot Actuator/Micrometer if enabled.
- When `fluxgate.openfeature.enabled` is true, the starter also registers an OpenFeature `Client` implementation. That client accepts flag keys, default values, and evaluation contexts (environment IDs are required). Evaluations performed through OpenFeature seamlessly delegate to FluxGate while preserving standard hooks and event listeners offered by OpenFeature.
- This dual approach makes FluxGate usable either directly (FluxGateClient) or through OpenFeature for vendor-neutral portability. Use OpenFeature to prevent lock-in and to benefit from existing SDKs across languages.

## Operational Notes

- **Kill switches**: Production-ready emergency toggles allow teams to disable/enable features instantly and optionally schedule auto-rollback between 5 and 60 minutes. The UI surfaces countdown timers and audit trails (who triggered the action, when it happened).
- **Approval workflows**: Pipelines/stages, approval policies, and dependency graphs ensure rollout governance; the UI organizes these into drag-and-drop ordering for criteria and stage prioritization.
- **Cluster synchronization**: Backend broadcasts updates so every edge node stays in sync; the UI reflects the authoritative state via GraphQL subscriptions and websockets.
- **Security**: Edge clients authenticate via client ID/secret; JWT secures GraphQL; CORS origins, TLS, and secret rotation are recommended for production.

## Next Steps

1. Ensure secret management and TLS are configured before exposing any public endpoints.
2. Provision clients (ID/secret) via backend for each downstream service or OpenFeature client.
3. Use the Spring starter’s metrics hooks to monitor edge health and evaluation latency in production dashboards.
4. Update the runtime UI `config.js` values when deploying across environments so each instance tours the correct backend/edge endpoints and websockets.

With this guidance, operators can configure FluxGate, integrate with Spring applications, hit the REST/OFREP APIs, and rely on the architecture’s safety mechanisms without needing to view implementation details.
