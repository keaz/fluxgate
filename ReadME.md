# FluxGate — Feature Flag Delivery Platform ![FluxGate Logo](./favicon.svg)

> **Important Note:** FluxGate is currently in **beta**. APIs, configuration, and deployment details may change.

A modern feature toggle management system for controlled rollouts, safe experimentation, and progressive delivery.

![System Overview](./media/new_evaluation.jpg)

- [Backend](https://hub.docker.com/r/keaz/flux-gate-backend): Rust (Actix-Web + async-graphql + tonic + sqlx + Postgres)
- [Edge](https://hub.docker.com/r/keaz/flux-gate-edge): Rust (Actix HTTP + tonic gRPC client, in-memory cache, analytics flushing)
- [UI](https://hub.docker.com/r/keaz/flux-gate-ui): React (Vite, Apollo Client, Tailwind)

## 🚀 What's New

### Feature Variants for A/B Testing
Go beyond boolean flags! Serve different values (strings, numbers, JSON objects) to different user segments. Perfect for UI experiments, pricing tests, and configuration management. With deterministic bucketing and flexible JSONB storage, run sophisticated multivariate experiments without deploying new code.

### Priority-Based Criteria Evaluation
Control the order of criteria evaluation with priority fields. Drag-and-drop UI makes it easy to reorder targeting rules visually. Lower priority values are evaluated first, giving you precise control over complex targeting logic and ensuring the right users get the right experience.

### Emergency Kill Switch with Auto-Rollback
Production incident? One click to safety. Instantly disable problematic features across all environments with automatic rollback scheduling (5-60 minutes). Includes centralized monitoring dashboard with countdown timers and complete audit trail.

### Real-Time Analytics Dashboard
See what's happening NOW, not what happened yesterday. Live metrics updated every 30 seconds via GraphQL subscriptions, with time-series visualization, flexible aggregation (1-60 minute intervals), and performance-optimized PostgreSQL queries.

### Modern Material Dashboard UI
Professional, polished interface matching Material Dashboard's design language with gradient buttons, elevated cards, comprehensive chart library (Line, Area, Bar, Pie, Donut), and sophisticated shadow hierarchy.

### Cluster Improvements
Enhanced gRPC streaming with proper feature update propagation across cluster nodes, ensuring edge server caches stay synchronized in multi-node deployments.

### Technical Achievements
- **Feature Variants System**: Flexible value storage supporting string, number, boolean, and JSON types
- **Priority-Based Evaluation**: Ordered criteria processing with drag-and-drop UI for intuitive management
- **280+ Unit Tests**: Comprehensive test coverage ensuring reliability
- **Production-Ready**: Robust error handling and full audit trails
- **High Performance**: Optimized queries and in-memory caching for sub-10ms evaluation
- **Type Safety**: Full TypeScript implementation in UI with React 19 and Tailwind CSS 4
- **Multi-Platform**: Docker images for amd64 and arm64 architectures

📹 **Demo Videos & Screenshots**: Check out the [media/](./media/) folder for system demonstrations and UI screenshots.


## 0.5) Feature Variants & Advanced Targeting

### Feature Variants for A/B Testing

FluxGate goes beyond simple boolean flags with **Feature Variants** - a powerful system for A/B testing and multivariate experiments:

**What are Variants?**
- Instead of just `true/false`, serve different values to different user segments
- Support for multiple data types: `string`, `number`, `boolean`, or complex `json` objects
- Each feature can have multiple named variants (e.g., "control", "variant-a", "variant-b")

**How it Works:**
1. Create variants for your feature with unique identifiers
2. Configure targeting criteria to specify which variant to serve to which users
3. Users matching specific criteria receive the corresponding variant value
4. Consistent experience - users always see the same variant

**Example Use Cases:**
- **UI Experiments**: Serve different button colors or layouts
  - Variant "control": `{"color": "blue", "size": "medium"}`
  - Variant "test-a": `{"color": "green", "size": "large"}`
- **Pricing Tests**: Different price points for user segments
  - Variant "standard": `{"price": 9.99, "currency": "USD"}`
  - Variant "premium": `{"price": 14.99, "currency": "USD"}`
- **Feature Configs**: Different configuration values
  - Variant "low": `{"timeout_ms": 1000, "retry_count": 3}`
  - Variant "high": `{"timeout_ms": 5000, "retry_count": 5}`

### Ordered Criteria Evaluation

**Priority-Based Targeting:**
- Control the order in which targeting rules are evaluated
- Rules with lower priority numbers are checked first
- First matching rule determines which variant users receive
- Enables precise control over complex targeting scenarios

**Visual Management:**
- Drag-and-drop interface for reordering targeting rules
- Real-time updates as you reorganize your criteria
- No manual priority management needed

**Why Order Matters:**
```
Priority 0: Premium users → Serve variant-a (50% rollout)
Priority 1: Beta users → Serve variant-b (100% rollout)
Priority 2: All others → Serve control (10% rollout)
```

With ordered evaluation, premium users always get their special treatment first, even if they're also in the beta group.


## 1) What FluxGate is

FluxGate is a full-stack feature flag platform that lets product and platform teams define, manage, and deliver features safely across environments. It provides:
- A backend with GraphQL (CRUD, auth, subscriptions) and gRPC (edge streaming, evaluation, user assignments)
- An edge service optimized for fast, cached, context-aware evaluations and analytics collection
- A React UI to administer teams, environments, pipelines/stages, features, contexts, clients, and RBAC

Big picture:
- UI → Backend GraphQL at /graphql for creation, updates, and real-time dashboards
- Edge → Backend gRPC for initial feature snapshot and incremental FeatureUpdate stream, plus evaluation/event push
- Backend → Postgres for persistence and migrations; broadcasts updates to subscribed edges


## 2) Key capabilities

- Feature modeling
  - Feature types (simple/contextual), multi-environment stages with order/position
  - **Feature Variants**: A/B testing with multiple values (not just boolean on/off)
    - Support for string, number, boolean, and JSON variant types
    - Stage criteria can specify which variant to serve
    - Flexible JSONB storage for complex variant payloads
  - **Ordered Criteria Evaluation**: Priority-based evaluation with drag-and-drop UI
    - Criteria evaluated in priority order (lower values first)
    - Visual reordering in UI for intuitive priority management
  - Relationships and dependencies
  - Contexts and stage criteria with rollout percentages (bucketing)
- Evaluation engine
  - Deterministic bucketing by sticky key, criteria checks, dependency gating
  - Kill switch integration for emergency feature disable
  - Used by both backend (for gRPC Evaluate) and edge server
- Delivery topology
  - Backend broadcasts feature updates via a shared tokio broadcast channel
  - Edge opens a long-lived gRPC stream to receive initial snapshot and incremental UPSERT/DELETE updates
  - Edge maintains an in-memory key/id cache for fast evaluations
  - Multi-node cluster support with synchronized update propagation
- Emergency controls
  - **Kill Switch**: One-click emergency disable/enable for any feature
  - **Auto-Rollback**: Schedule automatic re-enablement (5-60 minutes)
  - **Kill Switch Monitor**: Dashboard view of all disabled features with countdown timers
  - Complete audit trail with timestamps and user tracking
- Real-time analytics
  - **GraphQL Subscriptions**: Live metrics updated every 30 seconds
  - **Time-Series Data**: 24-hour evaluation tracking with configurable intervals (1-60 minutes)
  - **Dashboard Metrics**: Evaluation rates, success rates, cache hit rates
  - **Flexible Filtering**: By feature, environment, or client
  - Edge records evaluation events locally and flushes in batches to backend via gRPC
  - Backend persists events for dashboards and time-series analysis
- Modern UI/UX
  - **Material Dashboard Design**: Professional Material Design theme
  - **Chart Library**: 5 chart types (Line, Area, Bar, Pie, Donut) powered by Recharts
  - **Responsive Design**: Mobile-friendly with gradient buttons and elevated cards
  - **Real-time Updates**: WebSocket subscriptions with auto-reconnection
- Security & auth
  - JWT-based user auth for GraphQL
  - Role-Based Access Control for deployment workflows (Requester, Approver, Team Admin)
  - Client credentials for edge/SDK-style access to feature data


## 3) Architecture and components

- feature-toggle-backend (Rust)
  - HTTP (Actix-Web) GraphQL endpoint at /graphql with GraphiQL enabled
  - gRPC server (tonic) for edge connections.
  - Dependency-injected logic/repositories, SQLx Postgres
  - Broadcast channel delivers Feature Update messages to all subscribers
  - Config via config.toml (allowed_origin, http_addr, grpc_addr); DATABASE_URL required
- feature-edge-server (Rust)
  - HTTP endpoints: POST /evaluate, GET /health; Swagger UI at /docs
  - gRPC client to backend; maintains streaming subscription + cache
  - Sticky assignment cache; periodic flush of assignments and evaluation events
- evaluation-engine
  - Pure library with deterministic bucketing and criteria evaluation
- feature-toggle-ui (React)
  - Vite + Apollo Client; runtime GraphQL URLs via window.ENV or defaults
  - Container image generates runtime config.js using env vars (BACKEND_HOST, BACKEND_PORT, BACKEND_PROTOCOL, WS_PROTOCOL)

Data flow:
- UI ↔ Backend GraphQL for admin flows and dashboards
- Edge ↔ Backend gRPC for streaming feature data, evaluation, and analytics
- Backend ↔ Postgres for durable storage, migrations, and analytics persistence


## 3.1) SDKs and integrations

FluxGate provides native SDKs for easy integration with your applications:

### Spring Boot Starter (Java)
**Location**: `fluxgate-spring/fluxgate-spring-boot-starter/`

A production-ready Spring Boot starter for integrating Java applications with FluxGate Edge Server:

**Features**:
- **Auto-Configuration**: Zero-config setup with Spring Boot conventions
- **FluxGateClient Interface**: Simple, type-safe feature evaluation API
- **Retry Logic**: Built-in resilience with exponential backoff
- **Health Checks**: Spring Boot Actuator integration
- **Metrics**: Micrometer-based metrics for monitoring
- **Async Support**: Non-blocking evaluation with CompletableFuture
- **Context Mapping**: Easy context value injection for user targeting

**Maven Dependency**:
```xml
<dependency>
    <groupId>com.github.keaz</groupId>
    <artifactId>fluxgate-spring-boot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

**Configuration**:
```yaml
fluxgate:
  edge-url: http://localhost:8081
  timeout: 5s
  retry:
    max-attempts: 3
    backoff: 1s
```

**Usage**:
```java
@Autowired
private FluxGateClient fluxGateClient;

public void checkFeature() {
    Map<String, String> context = Map.of("userId", "123", "role", "admin");
    boolean enabled = fluxGateClient.evaluateFeature(
        "BetaUsers",
        "env-id",
        context
    );
}
```

**Documentation**: See [fluxgate-spring/fluxgate-spring-boot-starter/README.md](fluxgate-spring/fluxgate-spring-boot-starter/README.md) for full details.

### Direct Edge Server Integration

For custom integrations, use the Edge Server REST API:
- **Endpoint**: `POST /evaluate`
- **Documentation**: Swagger UI at `http://localhost:8081/docs`
- **Response Time**: Sub-10ms with in-memory caching


## 4) Quickstart: Docker Compose (local)


This quickstart launches the backend and UI using Docker Compose. Internal docker-compose.yml files are not exposed; use the following example to run both services together.

Prerequisites: Docker Desktop, docker compose

Create a file named `docker-compose.yml` in your project root with the following content:

```yaml
version: '3.8'
services:
  backend:
    image: keaz/flux-gate-backend:latest
    environment:
      - DATABASE_URL=postgres://postgres:local123@localhost:5432/feature_toggle
    ports:
      - "8080:8080" # GraphQL
    depends_on:
      - postgres
  ui:
    image: keaz/flux-gate-ui:latest
    environment:
      - BACKEND_HOST=backend
      - BACKEND_PORT=8080
      - BACKEND_PROTOCOL=http
      - WS_PROTOCOL=ws
    ports:
      - "3000:80"
    depends_on:
      - backend
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=local123
      - POSTGRES_DB=feature_toggle
    ports:
      - "5433:5432"
```

Usage:
- Start the stack:
  - `docker compose up --build -d`
- Follow logs:
  - `docker compose logs -f`
- Stop:
  - `docker compose down`

Ports (host):
- Postgres: 5433 → container 5432 (user: postgres, password: local123, db: feature_toggle — for local only)
- Backend: 8080 (GraphQL /graphql, GraphiQL)
- UI: 3000 (browse http://localhost:3000)

Notes:
- Replace default passwords, ports, and seeds for any shared environments


## 5) Screenshots and demos

FluxGate features a modern, professional UI built with Material Dashboard design principles.

### Demo Videos

**Feature Management & Evaluation**
- [System Overview Demo](./media/Screen%20Recording%202025-11-02%20at%2019.24.33.mov) - Complete walkthrough of the system overview dashboard with real-time metrics
- [Real-Time Analytics Demo](./media/Screen%20Recording%202025-11-02%20at%2020.52.04.mov) - Demonstration of real-time evaluation analytics and dashboard features
- [Quick Feature Demo](./media/My%20Movie.mp4) - Quick overview of feature management capabilities

### UI Screenshots

**System Overview Dashboard**
<div style="display: flex; gap: 10px; flex-wrap: wrap;">
  <img src="./media/system_overview.jpg" alt="System Overview Dashboard" width="400"/>
  <img src="./media/system_overview_2.jpg" alt="System Overview with Metrics" width="400"/>
</div>

**Feature Management with Variants**
<div style="display: flex; gap: 10px; flex-wrap: wrap;">
  <img src="./media/feature%20with%20variants.jpg" alt="Feature with Variants" width="400"/>
  <img src="./media/feature%20rolloout.jpg" alt="Feature Rollout" width="400"/>
</div>

**Traffic Management & Approval Policies**
<div style="display: flex; gap: 10px; flex-wrap: wrap;">
  <img src="./media/traffic_management.jpg" alt="Traffic Management" width="400"/>
  <img src="./media/approval_policy_creation.jpg" alt="Approval Policy Creation" width="400"/>
</div>

**Approvals Workflow**
<div style="display: flex; gap: 10px; flex-wrap: wrap;">
  <img src="./media/approvals.jpg" alt="Approvals Dashboard" width="400"/>
</div>

### Key UI Features Showcased

- **Material Dashboard Theme**: Gradient buttons, elevated cards, sophisticated shadow hierarchy
- **Real-Time Dashboards**: Live metrics with 30-second updates via GraphQL subscriptions
- **Kill Switch Monitor**: Emergency controls with countdown timers and audit trail
- **Chart Library**: Line, Area, Bar, Pie, and Donut charts powered by Recharts
- **Responsive Design**: Mobile-friendly with modern Material Design components


## 6) Kubernetes deployment (reference manifests)

Use your private registry images and a managed Postgres in production. The following is a minimal, single-namespace demo. Replace placeholders {{...}} and tune requests/limits, readiness/liveness probes, and storage.

Namespace:
```yaml path=null start=null
apiVersion: v1
kind: Namespace
metadata:
  name: fluxgate
```

Database URL Secret (example: managed Postgres or your own DSN):
```yaml path=null start=null
apiVersion: v1
kind: Secret
metadata:
  name: fluxgate-db
  namespace: fluxgate
type: Opaque
stringData:
  DATABASE_URL: "postgres://postgres:{{POSTGRES_PASSWORD}}@{{POSTGRES_HOST}}:5432/feature_toggle"
```

Backend Deployment + Service:
```yaml path=null start=null
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fluxgate-backend
  namespace: fluxgate
spec:
  replicas: 2
  selector:
    matchLabels: { app: fluxgate-backend }
  template:
    metadata:
      labels: { app: fluxgate-backend }
    spec:
      containers:
        - name: backend
          image: ghcr.io/your-org/fluxgate-backend:1.0.0
          imagePullPolicy: IfNotPresent
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: fluxgate-db
                  key: DATABASE_URL
          ports:
            - containerPort: 8080 # HTTP GraphQL
            - containerPort: 50051 # gRPC
          # Optional: mount custom config.toml if you need to override defaults
          # volumeMounts:
          #   - name: backend-config
          #     mountPath: /app/config.toml
          #     subPath: config.toml
      # volumes:
      #   - name: backend-config
      #     configMap:
      #       name: fluxgate-backend-config
---
apiVersion: v1
kind: Service
metadata:
  name: fluxgate-backend
  namespace: fluxgate
spec:
  selector: { app: fluxgate-backend }
  ports:
    - name: http
      port: 8080
      targetPort: 8080
    - name: grpc
      port: 50051
      targetPort: 50051
```

Edge Deployment + Service:
```yaml path=null start=null
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fluxgate-edge
  namespace: fluxgate
spec:
  replicas: 2
  selector:
    matchLabels: { app: fluxgate-edge }
  template:
    metadata:
      labels: { app: fluxgate-edge }
    spec:
      containers:
        - name: edge
          image: ghcr.io/your-org/fluxgate-edge:1.0.0
          imagePullPolicy: IfNotPresent
          env:
            - name: EDGE_BACKEND_GRPC
              value: "http://fluxgate-backend.fluxgate.svc.cluster.local:50051"
            - name: EDGE_HTTP_ADDR
              value: "0.0.0.0:8081"
            - name: EDGE_CLIENT_ID
              value: "{{CLIENT_ID_UUID}}"
            - name: EDGE_CLIENT_SECRET
              value: "{{CLIENT_API_KEY}}"
            - name: EDGE_ASSIGNMENT_FLUSH_SECS
              value: "10"
            - name: EDGE_EVALUATION_FLUSH_SECS
              value: "30"
          ports:
            - containerPort: 8081
---
apiVersion: v1
kind: Service
metadata:
  name: fluxgate-edge
  namespace: fluxgate
spec:
  selector: { app: fluxgate-edge }
  ports:
    - name: http
      port: 8081
      targetPort: 8081
```

UI Deployment + Service:
```yaml path=null start=null
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fluxgate-ui
  namespace: fluxgate
spec:
  replicas: 2
  selector:
    matchLabels: { app: fluxgate-ui }
  template:
    metadata:
      labels: { app: fluxgate-ui }
    spec:
      containers:
        - name: ui
          image: ghcr.io/your-org/fluxgate-ui:1.0.0
          imagePullPolicy: IfNotPresent
          env:
            - name: BACKEND_HOST
              value: fluxgate-backend.fluxgate.svc.cluster.local
            - name: BACKEND_PORT
              value: "8080"
            - name: BACKEND_PROTOCOL
              value: http
            - name: WS_PROTOCOL
              value: ws
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: fluxgate-ui
  namespace: fluxgate
spec:
  selector: { app: fluxgate-ui }
  ports:
    - name: http
      port: 80
      targetPort: 80
```

Optional Ingress (example NGINX Ingress; adjust hosts/TLS):
```yaml path=null start=null
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fluxgate
  namespace: fluxgate
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
    - host: fluxgate.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fluxgate-ui
                port:
                  number: 80
    - host: api.fluxgate.example.com
      http:
        paths:
          - path: /graphql
            pathType: Prefix
            backend:
              service:
                name: fluxgate-backend
                port:
                  number: 8080
    - host: edge.fluxgate.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fluxgate-edge
                port:
                  number: 8081
```

Apply order example:
- kubectl apply -f namespace.yaml
- kubectl apply -f secret-db.yaml
- kubectl apply -f backend.yaml
- kubectl apply -f edge.yaml
- kubectl apply -f ui.yaml
- kubectl apply -f ingress.yaml


## 7) Configuration reference

Backend (feature-toggle-backend):
- Required
  - DATABASE_URL: Postgres DSN; example postgres://user:pass@host:5432/feature_toggle
- Config file (feature-toggle/feature-toggle-backend/config.toml)
  - allowed_origin: CORS origin for UI (default http://localhost:5173)
  - http_addr: HTTP bind address (default 127.0.0.1:8080)
  - grpc_addr: gRPC bind address (default 0.0.0.0:50051)
  - jwt_secret: development default (production uses rotated secrets stored in DB)
- Logging
  - log4rs.yaml (bundled in image) controls levels/appenders
- Migrations & seed
  - Migrations under feature-toggle/feature-toggle-backend/migrations
  - Local/demo seed feature-toggle/init.sql

Edge (feature-edge-server):
- EDGE_BACKEND_GRPC: URL for backend gRPC (default http://127.0.0.1:50051)
- EDGE_HTTP_ADDR: HTTP bind (default 0.0.0.0:8081)
- EDGE_CLIENT_ID: UUID of client (provisioned in backend)
- EDGE_CLIENT_SECRET: API key for client (provisioned in backend)
- EDGE_ASSIGNMENT_FLUSH_SECS: Sticky assignment flush cadence (default 10)
- EDGE_EVALUATION_FLUSH_SECS: Evaluation events flush cadence (default 30)
- Logging: log4rs.yaml bundled in image

UI (feature-toggle-ui):
- Container runtime env generates /usr/share/nginx/html/config.js
  - BACKEND_HOST, BACKEND_PORT, BACKEND_PROTOCOL, WS_PROTOCOL
- Local dev (Vite): defaults to http://localhost:8080/graphql; you can inject window.ENV or adjust code to use VITE_ vars

Security notes (prod):
- Use a managed Postgres with strong credentials and network policies
- Do not ship with default jwt_secret; rely on backend’s secret management, and rotate regularly
- Create dedicated Clients (ID/SECRET) per app that calls the edge; restrict web origins as needed
- Serve UI and API over TLS (Ingress/NLB termination); restrict CORS to intended origins


## 8) Endpoints and ports

- Backend HTTP (GraphQL): /graphql, GraphiQL enabled
- Backend gRPC: port 50051
- Edge HTTP: /evaluate, /health; docs at /docs
- UI: port 80 (container), typically published via Ingress or host 3000 for local

### Feature Evaluation

FluxGate Edge Server supports both a custom evaluation API and the [OpenFeature Remote Evaluation Protocol (OFREP)](https://openfeature.dev/specification/ofrep) standard for feature flag evaluation.

#### Custom Evaluation API

**Simple Boolean Feature:**
```bash
curl --location 'http://localhost:8081/evaluate' \
--header 'Content-Type: application/json' \
--data '{
  "flagKey": "BetaUsers",
  "context": {
    "bucketingKey": "user-15",
    "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
    "userId": "15",
    "role": "admin"
  }
}'
```

**Response:**
```json
{
  "flagKey": "BetaUsers",
  "value": true,
  "variant": null,
  "reason": "TARGETED_MATCH"
}
```

**Feature with Variant:**
```bash
curl --location 'http://localhost:8081/evaluate' \
--header 'Content-Type: application/json' \
--data '{
  "flagKey": "checkout_button_text",
  "context": {
    "bucketingKey": "user-12345",
    "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
    "userId": "12345",
    "tier": "premium"
  }
}'
```

**Response:**
```json
{
  "flagKey": "checkout_button_text",
  "value": "Get Started Today",
  "variant": "variant-a",
  "reason": "TARGETED_MATCH"
}
```

#### OFREP (OpenFeature Remote Evaluation Protocol) API

FluxGate implements the [OFREP specification](https://openfeature.dev/specification/ofrep) for standards-based feature flag evaluation. OFREP provides a vendor-neutral protocol for remote feature flag evaluation.

**Endpoint:** `POST /ofrep/v1/evaluate/flags/{flagKey}`

**Boolean Flag Evaluation:**
```bash
curl --location 'http://localhost:8081/ofrep/v1/evaluate/flags/BetaUsers' \
--header 'Content-Type: application/json' \
--data '{
  "context": {
    "bucketingKey": "user-15",
    "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
    "userId": "15",
    "role": "admin"
  }
}'
```

**OFREP Response Format:**
```json
{
  "key": "BetaUsers",
  "value": true,
  "reason": "TARGETING_MATCH",
  "variant": null,
  "metadata": {}
}
```

**Variant Flag Evaluation:**
```bash
curl --location 'http://localhost:8081/ofrep/v1/evaluate/flags/checkout_button_text' \
--header 'Content-Type: application/json' \
--data '{
  "context": {
    "bucketingKey": "user-12345",
    "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
    "userId": "12345",
    "tier": "premium"
  }
}'
```

**Response:**
```json
{
  "key": "checkout_button_text",
  "value": "Get Started Today",
  "reason": "TARGETING_MATCH",
  "variant": "variant-a",
  "metadata": {}
}
```

**OFREP Response Fields:**
- `key`: The feature flag key that was evaluated
- `value`: The resolved flag value (boolean, string, number, or JSON object)
- `reason`: Evaluation reason code (e.g., `TARGETING_MATCH`, `DEFAULT`, `DISABLED`)
- `variant`: Optional variant identifier for A/B testing
- `metadata`: Additional evaluation metadata

**OFREP Benefits:**
- **Standards-Based**: Compatible with OpenFeature SDKs and ecosystem
- **Vendor-Neutral**: Easy migration between feature flag providers
- **Interoperable**: Works with any OFREP-compliant client
- **Future-Proof**: Follows industry-standard specification

For more details on the OFREP specification, see the [official OFREP documentation](https://openfeature.dev/specification/ofrep).

For more API examples and integration guides, see the [Edge Server API Reference](./fluxgate.wiki/Edge-Server-API.md).

### Feature Variant Operations (GraphQL)

**Create Feature Variant**
```graphql
mutation {
  createFeatureVariant(input: {
    featureId: "feature-uuid-here"
    control: "variant-a"
    value: "{\"color\": \"blue\", \"size\": \"large\"}"
    valueType: JSON
    description: "Blue large button variant"
  }) {
    id
    control
    value
    valueType
    description
  }
}
```

**Query Feature Variants**
```graphql
query {
  feature(id: "feature-uuid-here") {
    id
    key
    variants {
      id
      control
      value
      valueType
      description
    }
  }
}
```

**Update Stage Criteria with Priority and Variant**
```graphql
mutation {
  updateStageCriteria(input: {
    id: "criteria-uuid-here"
    priority: 0
    serve: "variant-a"
    enabled: true
    rolloutPercentage: 50
  }) {
    id
    priority
    serve
    enabled
  }
}
```

### Kill Switch Operations (GraphQL)

**Emergency Disable Feature (with optional auto-rollback)**
```graphql
mutation {
  emergencyDisableFeature(
    id: "feature-uuid-here"
    rollbackInMinutes: 30
  ) {
    id
    key
    killSwitchEnabled
    killSwitchActivatedAt
    rollbackScheduledAt
  }
}
```

**Emergency Enable Feature**
```graphql
mutation {
  emergencyEnableFeature(id: "feature-uuid-here") {
    id
    key
    killSwitchEnabled
    killSwitchActivatedAt
    rollbackScheduledAt
  }
}
```

### Real-Time Dashboard Subscriptions (GraphQL)

**Subscribe to Evaluation Rates**
```graphql
subscription {
  evaluationRates(input: {
    featureKey: "new_checkout_flow"
    environmentId: "production"
    intervalMinutes: 5
    durationHours: 2
  }) {
    timeBucket
    evaluationCount
    successCount
    successRate
    cacheHitRate
  }
}
```

**Subscribe to Evaluation Summary**
```graphql
subscription {
  evaluationSummary(input: {
    environmentId: "production"
    durationHours: 24
  }) {
    totalEvaluations
    successfulEvaluations
    successRate
    cacheHitRate
    generatedAt
  }
}
```


## 9) Local development commands (reference)

From feature-toggle/ (workspace):
- Build all: cargo build --workspace
- Run backend: cargo run -p feature-toggle-backend
- Run edge: cargo run -p feature-edge-server
- Tests (workspace): DATABASE_URL=postgres://postgres:local123@localhost:5432/feature_toggle cargo test --workspace
- Apply DB migrations (from feature-toggle/feature-toggle-backend): SQLX_OFFLINE=false DATABASE_URL=... sqlx migrate run

UI (feature-toggle-ui/):
- npm ci
- npm run dev | npm run build | npm run preview | npm run lint | npm run test


## 10) Observability and dashboards

FluxGate provides comprehensive real-time analytics and monitoring capabilities:

### Real-Time Analytics Dashboards

**System Overview Dashboard**
- Live system metrics updated every 30 seconds
- Total evaluations, active features, and cache hit rates
- Top 5 most evaluated features
- Feature growth trends and evaluation volume over time
- Activity feed showing recent system events

**Evaluation Analytics Dashboard**
- Time-series evaluation metrics with customizable intervals (1-60 minutes)
- Success rates and cache performance tracking
- Distribution charts (by feature, environment, client)
- Top features by evaluation count
- Filter by feature key, environment, or client ID
- View data across 1-24 hour time windows

**Feature Rollout Dashboard**
- Rollout health metrics and status monitoring
- Pending approvals list with workflow tracking
- Pipeline visualization showing deployment stages
- **Kill Switch Monitor**: Real-time view of disabled features with countdown timers
- Dependency graph visualization
- Rollout timeline with historical data

### GraphQL Subscriptions

Real-time data streaming via GraphQL subscriptions:
- `evaluationRates`: Time-bucketed evaluation metrics
- `evaluationSummary`: Aggregated statistics
- `evaluationDashboard`: Combined dashboard data
- 30-second update intervals with efficient WebSocket connections

### Kill Switch Monitoring

**Emergency Controls Dashboard**
- One-click feature disable/enable from feature table
- Kill Switch Monitor shows all disabled features
- Countdown timers for scheduled auto-rollback
- Complete audit trail with user and timestamp tracking
- Emergency disable with optional rollback scheduling (5-60 minutes)

### Technical Features

- **Backend**: log4rs configuration per service for logs
- **Database**: Evaluation analytics persisted with time-series aggregation
- **Edge**: /health endpoint for readiness checks
- **Backend**: GraphQL endpoint for liveness checks
- **UI**: Chart library with 5 chart types (Line, Area, Bar, Pie, Donut)
- **Real-time**: WebSocket subscriptions with auto-reconnection
- **Performance**: PostgreSQL time-bucketed queries with concurrent execution

**Documentation**: See [feature-toggle/DASHBOARD_IMPLEMENTATION.md](feature-toggle/DASHBOARD_IMPLEMENTATION.md) for implementation details.


## 11) Documentation & resources

### Feature Documentation
- **[Feature Variants & Priority Evaluation](#05-feature-variants--advanced-targeting)** - A/B testing with variants and ordered criteria evaluation
- **[KILL_SWITCH_FIX_SUMMARY.md](./KILL_SWITCH_FIX_SUMMARY.md)** - Complete kill switch implementation and logic fix details
- **[feature-toggle/DASHBOARD_IMPLEMENTATION.md](./feature-toggle/DASHBOARD_IMPLEMENTATION.md)** - Real-time analytics dashboard with GraphQL subscriptions
- **[CLUSTER_GRPC_FIX_SUMMARY.md](./CLUSTER_GRPC_FIX_SUMMARY.md)** - Cluster feature update propagation fix
- **[CLUSTER_TESTING_GUIDE.md](./CLUSTER_TESTING_GUIDE.md)** - Multi-node cluster testing guide

### UI Documentation
- **[feature-toggle-ui/MATERIAL_DASHBOARD_COMPLETE_THEME.md](./feature-toggle-ui/MATERIAL_DASHBOARD_COMPLETE_THEME.md)** - Material Dashboard theme implementation
- **[feature-toggle-ui/DASHBOARD_CHARTS_BG_CARD_MIGRATION.md](./feature-toggle-ui/DASHBOARD_CHARTS_BG_CARD_MIGRATION.md)** - Dashboard UI consistency updates
- **[feature-toggle-ui/CHART_COMPONENTS_DOCUMENTATION.md](./feature-toggle-ui/CHART_COMPONENTS_DOCUMENTATION.md)** - Chart library usage guide

### SDK & Integration
- **[fluxgate-spring/fluxgate-spring-boot-starter/README.md](./fluxgate-spring/fluxgate-spring-boot-starter/README.md)** - Spring Boot integration guide

### Development Guides
- **[CLAUDE.md](./CLAUDE.md)** - Comprehensive development guide for contributors
- **[feature-toggle/ReadME.md](./feature-toggle/ReadME.md)** - Backend workspace details
- **[feature-toggle-ui/README.md](./feature-toggle-ui/README.md)** - UI development guide

### Docker Images
- **[Backend](https://hub.docker.com/r/keaz/flux-gate-backend)** - FluxGate Backend (Rust)
- **[Edge](https://hub.docker.com/r/keaz/flux-gate-edge)** - FluxGate Edge Server (Rust)
- **[UI](https://hub.docker.com/r/keaz/flux-gate-ui)** - FluxGate UI (React)

### User Guides (Wiki)
- **[User Guide Home](./fluxgate.wiki/Home.md)** - Getting started with FluxGate
- **[Feature Variants Guide](./fluxgate.wiki/Feature-Variants.md)** - Complete guide to A/B testing with variants
- **[Priority-Based Targeting](./fluxgate.wiki/Priority-Evaluation.md)** - Control evaluation order with priorities
- **[Edge Server API Reference](./fluxgate.wiki/Edge-Server-API.md)** - API documentation with request/response examples

### Support & Community
- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Join community discussions on GitHub

