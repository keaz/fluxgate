# 02 · Install and first boot

| Field | Value |
|---|---|
| Website section | Get started › Install |
| Length target | 3:30 |
| Takeaway | You can run the full FluxGate stack locally with Docker Compose and create the first admin in under five minutes. |
| Start state | Fresh machine with Docker. |
| End state | FluxGate running (backend 8080, edge 8081, UI 3000); `admin` signed in; no team. |
| Prerequisites | Docker, `openssl`, and the repository checked out on branch `cli-followups`. |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Terminal in the repository root, empty prompt. | You can run FluxGate locally in under five minutes. You need Docker and a terminal. |  |
| 0:07 | Terminal: run `openssl rand -base64 32`, then `export FLUXGATE_ENCRYPTION_KEY=<redacted>`. | First, an encryption key. FluxGate encrypts secrets it stores, such as Jira write-back tokens and single sign-on client secrets, and the key comes from an environment variable. Generate 32 random bytes, base64 encoded, and export them as FLUXGATE_ENCRYPTION_KEY. | Blur the generated key |
| 0:28 | Terminal: type `export TYPESAFE_API_KEY=<redacted>` but leave it unrun, or show the line commented out. | There is also an optional TYPESAFE_API_KEY. It turns on the AI features, and you only need it for video 14, so skip it for now. | Text overlay: optional, video 14 |
| 0:40 | Editor with `config.toml` open at the `allowed_origin` line, then scroll down. | Next, config.toml. The allowed_origin value is the browser origin the backend accepts for cross-origin requests, so point it at the UI. The http_addr and grpc_addr values are where the REST and gRPC servers listen: ports 8080 and 50051. | Highlight each key as it is named |
| 1:00 | Same file, highlight `public_base_url`. | And public_base_url is the address browsers and identity providers use to reach the backend. Single sign-on callbacks are built from it, and in video 12 Jira needs a public address to reach the backend too. When it is unset FluxGate guesses from each request, which is fine on localhost and not behind a proxy. | Highlight `public_base_url` |
| 1:26 | Terminal: run `docker compose up -d`, then `docker compose ps`. | Now start everything with docker compose up. Compose pulls and starts four containers: the backend, the UI, Postgres, and the edge server. Migrations run on backend startup, so there is no schema step to run by hand. | Label each container in `docker compose ps` |
| 1:46 | Browser at `http://localhost:8080/docs`. | While that settles, open the backend at slash docs. This is the Swagger UI for the REST API, handy when you want to see exactly what the UI and the CLI call. |  |
| 2:02 | Browser at `http://localhost:3000`; it redirects to `/create-admin`. | Now open the UI on port 3000. With no users yet, it sends you to the create admin page. This only happens once, on a fresh database. | Highlight the URL change |
| 2:15 | On "Create Admin Account", fill "Username" `admin`, "Password", "Confirm Password", "First Name", "Last Name", "Email", then click "Create Admin". | Fill in the form. Use admin as the username, choose a password, add a name and an email, then click create admin. This account has full control of the instance. | Blur the password fields |
| 2:32 | Login at `/login`: fill "Username" and "Password", click "Sign in". | FluxGate returns you to the sign in page. Enter the credentials you just created and click sign in. | Blur the password field |
| 2:43 | Land on "System Overview" at `/dashboard/overview`, mostly empty KPI cards. | You are in. The System Overview is empty because nothing exists yet: no features, no clients, no evaluations. The backend is on 8080, the edge server on 8081 and the UI on 3000. | Callout: ports 8080, 8081, 3000 |
| 2:59 | Same page, then the "Settings" group in the sidebar. | Before you can model a release you need people to do it, and approvals need more than one of them. Next, create a team and two users. |  |

## Hand-off

Next: create the Checkout team and the users `priya` and `sam`, and review roles (video 03).

## Gotchas while recording

- Record from branch `cli-followups` in `feature-toggle-cli-followups`; the first-admin bug on main makes some workers return 401 after the first admin is created until restart.
- Secrets typed or generated on screen are `<redacted>`: blur the output of `openssl rand -base64 32`, the `FLUXGATE_ENCRYPTION_KEY` and `TYPESAFE_API_KEY` values, and the admin password fields.
- The root `docker-compose.yml` starts backend, ui and postgres only; it has no edge service and does not pass `FLUXGATE_ENCRYPTION_KEY` into the backend. The `docker-compose.yml` in `feature-toggle-cli-followups` has backend and edge but no UI and no Postgres. Before recording, prepare one compose file with all four services (`feature_edge_server` with `EDGE_BACKEND_GRPC`, `EDGE_HTTP_ADDR`, `EDGE_CLIENT_ID`, `EDGE_CLIENT_SECRET`) and pass `FLUXGATE_ENCRYPTION_KEY=${FLUXGATE_ENCRYPTION_KEY}` to the backend. Never show the edge client secret line; keep it in an env file and blur if visible.
- The repository `config.toml` sets `allowed_origin` to `http://localhost:8090`. For this recording set it to `http://localhost:3000` so the UI on port 3000 works. Leave `public_base_url` commented or set it to `http://localhost:8080`.
- Deviation from the brief: the brief says `public_base_url` matters for the Jira Events URL. In the code the UI builds the Events URL from its own REST base URL (`feature-toggle-ui/src/utils/jiraIntegrations.ts:11-17`); `public_base_url` drives SSO callbacks (see `config.toml` comments). The voiceover therefore says Jira needs a public address to reach the backend, not that `public_base_url` sets the Events URL.
- Compose ports: backend 8080 (REST), UI 3000 (container port 80), Postgres 5433 on the host. gRPC 50051 is only published inside the compose network in the cli-followups file; publish it only if the edge runs outside Docker.
- The create admin page title is "Create Admin Account" and the submit button is "Create Admin" (`feature-toggle-ui/src/pages/CreateAdmin.tsx`). The login title is "Sign in to FluxGate" with submit "Sign in" (`Login.tsx`).
- Compose can take a minute on first pull; cut the wait in editing and keep the `docker compose ps` frame.
