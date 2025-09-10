# FluxGate — Feature Flag Delivery Platform

A modern feature toggle management system for controlled rollouts, safe experimentation, and progressive delivery.

![Edit Feature](./edit-feature.png)

- [Backend](https://hub.docker.com/r/keaz/flux-gate-backend): Rust (Actix-Web + async-graphql + tonic + sqlx + Postgres)
- [Edge](https://hub.docker.com/r/keaz/flux-gate-edge): Rust (Actix HTTP + tonic gRPC client, in-memory cache, analytics flushing)
- [UI](https://hub.docker.com/r/keaz/flux-gate-ui): React (Vite, Apollo Client, Tailwind)


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
  - Relationships and dependencies
  - Contexts and stage criteria with rollout percentages (bucketing)
- Evaluation engine
  - Deterministic bucketing by sticky key, criteria checks, dependency gating
  - Used by both backend (for gRPC Evaluate) and edge server
- Delivery topology
  - Backend broadcasts feature updates via a shared tokio broadcast channel
  - Edge opens a long-lived gRPC stream to receive initial snapshot and incremental UPSERT/DELETE updates
  - Edge maintains an in-memory key/id cache for fast evaluations
- Analytics
  - Edge records evaluation events locally and flushes in batches to backend via gRPC
  - Backend persists events for dashboards and time-series analysis
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

- log4rs configuration per service for logs
- Evaluation analytics persisted by backend for dashboards (see feature-toggle/DASHBOARD_IMPLEMENTATION.md)
- Edge exposes /health for readiness checks; backend GraphQL is a simple liveness check

