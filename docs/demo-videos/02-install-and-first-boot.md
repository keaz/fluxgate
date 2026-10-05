# 02 · Install and first boot

| Field | Value |
|---|---|
| Website section | Get started › Install |
| Length target | 3:30 |
| Takeaway | You can run the full FluxGate stack locally with Docker Compose and create the first admin in under five minutes. |
| Start state | Fresh machine with Docker. |
| End state | FluxGate running (backend 8080, UI 3000); edge server defined but not started (starts in 08); `admin` signed in; no team. |
| Prerequisites | Docker, `openssl`, and this repository cloned (images come from Docker Hub). The stack is `docs/demo-videos/assets/docker-compose.demo.yml`. |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Terminal in the repository root, empty prompt. | You can run FluxGate locally in under five minutes. You need Docker and a terminal. |  |
| 0:07 | Terminal: run `openssl rand -base64 32`, then `export FLUXGATE_ENCRYPTION_KEY=<redacted>`. | First, an encryption key. FluxGate encrypts secrets it stores, such as Jira write-back tokens and single sign-on client secrets, and the key comes from an environment variable. Generate 32 random bytes, base64 encoded, and export them as FLUXGATE_ENCRYPTION_KEY. | Blur the generated key |
| 0:28 | Terminal: type `export TYPESAFE_API_KEY=<redacted>` but leave it unrun, or show the line commented out. | There is also an optional TYPESAFE_API_KEY. It turns on the AI features, and you only need it for video 14, so skip it for now. | Text overlay: optional, video 14 |
| 0:40 | Editor with `docs/demo-videos/assets/config.demo.toml` open at the `allowed_origin` line, then scroll down. | Next, the backend config file. The demo stack mounts config.demo.toml into the backend container. The allowed_origin value is the browser origin the backend accepts for cross-origin requests, so it points at the UI on port 3000. The http_addr and grpc_addr values are where the REST and gRPC servers listen: ports 8080 and 50051. | Highlight each key as it is named |
| 1:07 | Same file, highlight `public_base_url`. | And public_base_url is the address browsers and identity providers use to reach the backend. Single sign-on callbacks are built from it, and in video 12 Jira needs a public address to reach the backend too. When it is unset FluxGate guesses from each request, which is fine on localhost and not behind a proxy. | Highlight `public_base_url` |
| 1:33 | Terminal: run `docker compose -f docs/demo-videos/assets/docker-compose.demo.yml up -d`, then `docker compose -f docs/demo-videos/assets/docker-compose.demo.yml ps`. | Now start the stack with docker compose up, pointing at the demo compose file. Three containers start: Postgres, the backend and the UI. Migrations run on backend startup, so there is no schema step to run by hand. The edge server is defined in the same file but waits until video 8, when you have a client for it to use. | Label each container in `docker compose ps` |
| 2:03 | Browser at `http://localhost:8080/docs`. | While that settles, open the backend at slash docs. This is the Swagger UI for the REST API, handy when you want to see exactly what the UI and the CLI call. |  |
| 2:19 | Browser at `http://localhost:3000`; it redirects to `/create-admin`. | Now open the UI on port 3000. With no users yet, it sends you to the create admin page. This only happens once, on a fresh database. | Highlight the URL change |
| 2:32 | On "Create Admin Account", fill "Username" `admin`, "Password", "Confirm Password", "First Name", "Last Name", "Email", then click "Create Admin". | Fill in the form. Use admin as the username, choose a password, add a name and an email, then click create admin. This account has full control of the instance. | Blur the password fields |
| 2:49 | Login at `/login`: fill "Username" and "Password", click "Sign in". | FluxGate returns you to the sign in page. Enter the credentials you just created and click sign in. | Blur the password field |
| 3:00 | Land on "System Overview" at `/dashboard/overview`, mostly empty KPI cards. | You are in. The System Overview is empty because nothing exists yet: no features, no clients, no evaluations. The backend is on 8080 and the UI on 3000. The edge server on 8081 comes in video 8. | Callout: ports 8080, 3000 |
| 3:18 | Same page, then the "Settings" group in the sidebar. | Before you can model a release you need people to do it, and approvals need more than one of them. Next, create a team and two users. |  |

## Hand-off

Next: create the Checkout team and the users `priya` and `sam`, and review roles (video 03).

## Gotchas while recording

- Checkouts: clone this repository for the compose file and config; the compose file pulls published images, so no source build is needed. Record with a backend image built from branch `cli-followups` (first-admin 401 bug on main makes other workers return 401 until restart): build it from `feature-toggle-cli-followups` with `docker build -f feature-toggle-backend/Dockerfile -t fluxgate-backend:cli-followups .` and run `export FLUXGATE_BACKEND_IMAGE=fluxgate-backend:cli-followups` before `docker compose up`. Viewers can use the default image.
- Secrets typed or generated on screen are `<redacted>`: blur the output of `openssl rand -base64 32`, the `FLUXGATE_ENCRYPTION_KEY` and `TYPESAFE_API_KEY` values, and the admin password fields.
- Demo compose: `docs/demo-videos/assets/docker-compose.demo.yml` runs postgres, backend and ui; the `edge` service is behind profile `edge` and is started in video 08. It passes `FLUXGATE_ENCRYPTION_KEY` (required, compose refuses to start without it) and optional `TYPESAFE_API_KEY` from the host environment. The root `docker-compose.yml` has no edge service and does not pass the encryption key; the `feature-toggle` and `feature-toggle-cli-followups` compose files build from source and have no UI or Postgres, which is why the demo file exists. Docker was not available when this file was written, so validate with `docker compose -f docs/demo-videos/assets/docker-compose.demo.yml config` before recording.
- Config path: the demo stack mounts `docs/demo-videos/assets/config.demo.toml` (same keys as the backend `config.toml`: `allowed_origin` set to `http://localhost:3000`, `http_addr`, `grpc_addr`, `public_base_url` commented out). Do not edit the nested repo `config.toml`.
- Deviation from the brief: the brief says `public_base_url` matters for the Jira Events URL. In the code the UI builds the Events URL from its own REST base URL (`feature-toggle-ui/src/utils/jiraIntegrations.ts:11-17`); `public_base_url` drives SSO callbacks (see `config.toml` comments). The voiceover therefore says Jira needs a public address to reach the backend, not that `public_base_url` sets the Events URL.
- Compose ports: backend 8080 (REST), UI 3000 (container port 80), Postgres 5433 on the host. The backend gRPC port 50051 is not published; the edge container reaches it over the compose network at `http://backend:50051`.
- The create admin page title is "Create Admin Account" and the submit button is "Create Admin" (`feature-toggle-ui/src/pages/CreateAdmin.tsx`). The login title is "Sign in to FluxGate" with submit "Sign in" (`Login.tsx`).
- Edge credentials for video 08: the edge needs `EDGE_CLIENT_ID` and `EDGE_CLIENT_SECRET` (`feature-toggle/feature-edge-server/CONFIG.md:11`; startup fails with `Failed to load configuration` if missing). These are a regular client's id (UUID) and API key: the edge sends them to the backend gRPC service, which looks up the client by UUID and checks its secret (`feature-toggle-backend/src/grpc/mod.rs` `verify_client_status`, around line 1107; edge side `feature-edge-server/src/grpc_client.rs:63-76`). So in video 08 create a client on the "Clients" page (`ClientCreate.tsx` shows the one-time "API Key"), then `export EDGE_CLIENT_ID=<client id>` and `export EDGE_CLIENT_SECRET=<redacted>` and run `docker compose -f docs/demo-videos/assets/docker-compose.demo.yml --profile edge up -d`. The seeded id in `init.sql` is for test data only; do not use it. Do not use a System Client.
- Compose can take a minute on first pull; cut the wait in editing and keep the `docker compose ps` frame.
