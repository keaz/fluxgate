# 16 · Going to production

| Field | Value |
|---|---|
| Website section | Observe and operate › Production deployment |
| Length target | 3:30 |
| Takeaway | A production FluxGate is pinned images, a managed database, two secrets, TLS in front, an edge near your apps, single sign-on and a JWT secret you can rotate. |
| Start state | Fresh production host with Docker Hub access; FluxGate not yet installed there. |
| End state | Production checklist covered; SSO configured; JWT emergency actions shown. |
| Prerequisites | A container host you control, a managed Postgres database, a reverse proxy or load balancer that holds your TLS certificate, and an OpenID Connect provider. For the UI scenes, a running FluxGate with `admin` signed in and team `Checkout` selected in "Select team". |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Editor with an empty `docker-compose.production.yml` next to a terminal. | The demo stack proves FluxGate works. Production needs decisions: which versions, where secrets live, and who terminates TLS. Here is the checklist. | |
| 0:12 | Editor: type block A from Code on screen. Highlight the three `image:` lines ending in `v1.2.0`, then the backend `DATABASE_URL` line; its value is `<redacted>`. | Pin all three images to v1.2.0: backend, edge and UI. A moving tag can change under you on a restart. Point the backend at a managed Postgres with DATABASE_URL. The backend applies its database migrations at startup, so back up the database before each upgrade. Run one backend instance. | Highlight the three `image:` lines |
| 0:38 | Same file: highlight the `FLUXGATE_ENCRYPTION_KEY` and `TYPESAFE_API_KEY` lines, values `<redacted>`. Terminal: run `openssl rand -base64 32`, output blurred. | Set FLUXGATE_ENCRYPTION_KEY: base64 of 32 random bytes. It encrypts the secrets FluxGate stores, like single sign-on client secrets and Jira tokens, and if it changes they stop decrypting. TYPESAFE_API_KEY is optional and only enables Jev. Keep both in your secret manager. | Blur the generated key |
| 1:00 | Editor: type block B from Code on screen, `config.toml`. Highlight each key as it is named. | Mount a config file into the backend. Set allowed_origin to the exact HTTPS address of your UI, since browser requests are checked against it. Set http_addr and grpc_addr for the listeners. Set public_base_url to the backend's public HTTPS address: single sign-on callbacks are built from it. | Highlight each key as it is named |
| 1:26 | Back to block A, the `ui` service with `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_PROTOCOL` and `WS_PROTOCOL`. | Terminate TLS at a reverse proxy or load balancer you own, with your certificate. Forward cookies on the single sign-on path, pass WebSocket upgrades and set the forwarded headers. The browser calls the backend directly, so point the UI container's variables at the public HTTPS address. Keep the gRPC port private; only edges need it. | Overlay diagram: browser to proxy (TLS) to UI and backend; gRPC stays inside |
| 1:52 | Block A, the `edge` service: `EDGE_BACKEND_GRPC`, `EDGE_HTTP_ADDR`, `EDGE_CLIENT_ID`, `EDGE_CLIENT_SECRET`; the secret value is `<redacted>`. | Run the edge close to your apps, in the same network or cluster, so evaluations stay local. Give it four settings: EDGE_BACKEND_GRPC, EDGE_HTTP_ADDR, EDGE_CLIENT_ID and EDGE_CLIENT_SECRET. The client credentials come from a client you created in the UI. | Highlight the four `EDGE_` names |
| 2:14 | Browser, signed in as `admin`. Click "Single Sign-On" in "Settings" to open `/settings/sso`, titled "Single sign-on". Click "Add provider". In "Add SSO provider" point at "Display name", "Slug", "Issuer URL", "Redirect URI", "Client ID", "Client secret" (blurred), "Groups claim" and "Role sync mode". Fill a sandbox provider and click "Create provider". Click the "Group mappings" icon on its row, click "Add mapping", type `checkout-approvers` in "IdP group value", choose "Role" and the role `Approver`, then click "Save mappings". The toast reads "Group mappings saved". Point at the "Enforce single sign-on" switch and its warning; leave it off. | Now sign-in. Single sign-on lets people use your OpenID Connect provider instead of another password. Add a provider with its issuer, client ID and secret, and register the redirect URI shown here at the provider. The match is exact, so use the same public address as public_base_url. Group mappings turn identity provider groups into roles, teams or admin access. Enforce single sign-on turns off password sign-in, except for break-glass admins you made by hand. Switch it on only after a test login works. | Highlight "Redirect URI", then the enforce warning |
| 2:56 | Click "JWT Settings" in "Settings" to open `/settings/jwt`, "JWT Secret Management". Point at "Security Notice" and "Current JWT Secrets" (previews blurred). Scroll to "Emergency Actions", click "Deactivate All JWT Secrets", point at "Confirm Deactivation", then click "Cancel". | FluxGate signs authentication tokens with a JWT secret. Rotate it from this page with Generate New Secret; existing tokens keep working until they expire. Under Emergency Actions, Deactivate All JWT Secrets signs everyone out at once. Keep it for a leaked secret. | Highlight "Emergency Actions" |
| 3:18 | The "Single sign-on" page, then `/dashboard/overview`. | That is the checklist: pinned images, a managed database, two secrets, TLS in front, an edge near your apps, and single sign-on. | |

## Code on screen

Block A: `docker-compose.production.yml`, a sketch to adapt to your platform. The database is managed, so there is no Postgres service. Values shown as `<redacted>` stay blurred or hidden.

```yaml
services:
  backend:
    image: keaz/flux-gate-backend:v1.2.0
    environment:
      DATABASE_URL: postgres://fluxgate:<redacted>@db.internal:5432/feature_toggle?sslmode=require
      FLUXGATE_ENCRYPTION_KEY: <redacted>
      # Optional: turns on the Jev AI features
      TYPESAFE_API_KEY: <redacted>
    volumes:
      - ./config.toml:/app/config/config.toml:ro
    ports:
      - "8080:8080" # REST API: reach it through your proxy
      # gRPC on 50051 stays on the private network; only edges use it

  ui:
    image: keaz/flux-gate-ui:v1.2.0
    environment:
      # The browser calls the backend directly: use its public address
      BACKEND_HOST: fluxgate-api.example.com
      BACKEND_PORT: "443"
      BACKEND_PROTOCOL: https
      WS_PROTOCOL: wss
    ports:
      - "3000:80"

  edge:
    image: keaz/flux-gate-edge:v1.2.0
    environment:
      EDGE_BACKEND_GRPC: http://backend:50051
      EDGE_HTTP_ADDR: 0.0.0.0:8081
      EDGE_CLIENT_ID: <client id from the Clients page>
      EDGE_CLIENT_SECRET: <redacted>
    ports:
      - "8081:8081"
```

Block B: `config.toml`, mounted into the backend container.

```toml
# The UI's origin, exactly as the browser shows it
allowed_origin = "https://fluxgate.example.com"

# Where the REST and gRPC servers listen inside the container
http_addr = "0.0.0.0:8080"
grpc_addr = "0.0.0.0:50051"

# The backend's public address; single sign-on callbacks are built from it
public_base_url = "https://fluxgate-api.example.com"
```

## Hand-off

End of the series. Back to the start (video 01), or to the section of the website you are setting up.

## Gotchas while recording

- Public-facing rule: the source repositories are private, so the viewer only has the images `keaz/flux-gate-backend`, `keaz/flux-gate-edge` and `keaz/flux-gate-ui` at `v1.2.0`. The scenes, voiceover and blocks use nothing else: no `kubectl`, no manifests, no repo paths. The `k8s/` kustomize overlays are deliberately not used: `k8s/overlays/production/kustomization.yaml:200` still ships a `jwt_secret` key that the backend config no longer has (`feature-toggle-backend/src/config.rs:10-40`), `k8s/edge.yaml:27-29` uses `EDGE_ASSIGNMENT_FLUSH_SECS` where the edge expects `EDGE_FLUSH__ASSIGNMENT_FLUSH_SECS` (`feature-edge-server/CONFIG.md`, Environment Variable Overrides), and none of them set `FLUXGATE_ENCRYPTION_KEY` or `TYPESAFE_API_KEY` (spec §6 #5). Never open the committed certificate and private key files in the `k8s/` directory on camera; the TLS scene shows no certificate at all.
- The `v1.2.0` tags do not exist on Docker Hub yet. Checked on 2026-10-05: the backend and edge repositories list `v1.1.5` as the newest version tag and the UI repository lists `v1.1.1` (plus `latest`). Publish all three at `v1.2.0` before this video ships, or change the tag everywhere in block A and the voiceover. Re-check with `docker pull` before recording.
- Verified facts. Backend config keys: `allowed_origin`, `http_addr`, `grpc_addr`, `public_base_url` (`config.rs:12-29`, `from_toml` trims a trailing slash `:317-333`); the callback is `<public_base_url>/api/v1/auth/sso/<slug>/callback`, built from the request when the key is unset, which is why it is set in production (`config.rs:23-29`, `feature-toggle/docs/sso.md:48`). The file is read from `/app/config/config.toml` in the container: the entrypoint copies it to `/app/config.toml` (`feature-toggle/scripts/backend-entrypoint.sh:8-15`); without a mount it falls back to a default config. The entrypoint runs `sqlx migrate run` before the app starts (`:25-28`), which is the basis for "back up the database before each upgrade". `DATABASE_URL` is read at startup (`database/mod.rs:47`) and the entrypoint masks its password in logs (`:5-6`). `FLUXGATE_ENCRYPTION_KEY` is base64 of exactly 32 bytes (`logic/secret_box.rs:3-4,23-25`), seals SSO client secrets (`logic/sso_provider.rs:35-36`) and Jira credentials (`logic/jira_integration_tx.rs:428,559`); a changed key breaks stored secrets (`docs/sso.md`, FLUXGATE_ENCRYPTION_KEY paragraph). `TYPESAFE_API_KEY` is read only from the environment and only turns Jev on (`config.rs:30-31`, `lib.rs:62-67`). Edge settings and names: `EDGE_BACKEND_GRPC`, `EDGE_HTTP_ADDR`, `EDGE_CLIENT_ID`, `EDGE_CLIENT_SECRET`, all required with no default (`feature-edge-server/CONFIG.md:5-11` and the Environment Variable Overrides section). UI container variables `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_PROTOCOL`, `WS_PROTOCOL` become `REST_HTTP_URL` and `REST_WS_URL` in `config.js` in the browser (`feature-toggle-ui/docker-entrypoint.sh:12-15`), so they must be the public addresses (`feature-toggle-ui/DOCKER_DEPLOYMENT.md:37`, Production with HTTPS Backend). Ports: backend exposes 8080 and 50051 (`feature-toggle-backend/Dockerfile:75`), edge 8081 (`feature-edge-server/Dockerfile:59`).
- One backend instance. The config has an optional `[cluster]` section with `enabled`, `listen_addr`, `discovery`, `node_id` and `reconnect_delay_ms` (`config.rs:17-19`, `cluster/mod.rs:84-110`), and the code starts it (`lib.rs:227`), so the keys exist in the image. The script still says to run one backend instance because that is how the product is designed to run (project decision, 2026-10-03: multi-instance races are not a design concern). Scale the edge, not the backend. If that policy changes, add a scene and the `[cluster]` keys to block B.
- Do not show the committed edge `config.toml` or any key file. Block A shows the edge secret as `<redacted>`; the real client id and API key come from a client created in the UI (video 08, Gotchas). `EDGE_CLIENT_ID` is a client UUID, not the SDK key.
- The edge is exposed on 8081 in block A as in the demo stack, but `POST /evaluate` is unauthenticated (video 08, Gotchas). The voiceover only says to keep gRPC private and run the edge near the apps; it does not say how to expose 8081. In a real deployment keep 8081 on a private network or behind the proxy.
- Proxy facts behind the TLS line. The state cookie `fluxgate_sso_state` has `Path=/api/v1/auth/sso/` and a proxy that strips it breaks every login with `sso_state_invalid` (`docs/sso.md:24-26`). Without `public_base_url` the backend trusts `Forwarded` and `X-Forwarded-*` headers, so the proxy must set them and strip client-supplied ones (`docs/sso.md:48`). The UI opens a WebSocket at `/api/v1/ws` (`docker-entrypoint.sh:15`), so the proxy must pass upgrades. Optional, not in the voiceover: `[device_login] trusted_proxies` lists the proxy addresses for CLI login rate limits (`config.rs:54-58`); add it to block B if you want it on screen.
- Redirect URI mismatch risk. The "Redirect URI" in the dialog is built by the UI as `<REST_HTTP_URL>/auth/sso/<slug>/callback` (`api/sso.ts:121-124`). With `BACKEND_PORT: "443"` as in block A, `REST_HTTP_URL` is `https://fluxgate-api.example.com:443/api/v1`, so a real production dialog shows `:443`, while the backend sends `<public_base_url>/api/v1/auth/sso/<slug>/callback` to the identity provider without a port. The match at the provider is exact (`docs/sso.md:90`), hence the voiceover line about using the same address as `public_base_url`. On the recording stack (localhost, port 8080) the dialog and the backend agree. Use "Test connection" after saving to check the issuer only; it does not check the redirect URI.
- Labels: the nav item is "Single Sign-On" (`layout/navConfig.ts:123`), the page title "Single sign-on" (`pages/SsoSettings.tsx:58`); the nav item "JWT Settings" (`navConfig.ts:124`) opens "JWT Secret Management" (`pages/JwtSettings.tsx:127`). Dialog "Add SSO provider" with "Display name", "Slug", "Issuer URL", "Redirect URI", "Client ID", "Client secret", "Groups claim", "Role sync mode" and button "Create provider" (`components/sso/SsoProviderForm.tsx`, dialog `:195-420`). Mappings: row action titled "Group mappings" (`SsoProviderList.tsx:62`), dialog "Group mappings for <name>" (`SsoMappingsEditor.tsx:110`), input aria-label "Group value" with placeholder "IdP group value" (`:143-145`), "Target type" options "Role", "Team", "Admin" (`:156-158`), "Add mapping" (`:192`), "Save mappings" (`:202`), toast "Group mappings saved" (`:97`). The enforce switch is "Enforce single sign-on" (`EnforceSsoToggle.tsx:52`) with the warning "Only break-glass admins (made admin manually, not through single sign-on) can still sign in with a password." (`:67`). The brief's "group-to-role mappings" are called "Group mappings" in the UI, and they also map to teams or admin access (`SsoMappingsEditor.tsx:112`).
- SSO setup needs a real OIDC provider. Use a sandbox one (a throwaway Keycloak or a developer tenant) and register its redirect URI before the take. Slug `sandbox-idp`, issuer from the sandbox; blur "Client ID" and "Client secret". Map a group your sandbox user belongs to, so a test login can follow off camera. The "Role" target needs the role `Approver` from video 03 to exist (`SsoMappingsEditor.tsx:48-52`). Do not switch "Enforce single sign-on" on while recording: it disables password sign-in for everyone but break-glass admins, and a wrong provider setting would lock people out. It saves immediately when toggled (`EnforceSsoToggle.tsx:29-45`). Only a system admin sees the page (`SsoSettings.tsx:114-124`) and the group "Settings" is collapsible in the sidebar (`navConfig.ts:110-114`).
- JWT page. "Emergency Actions" renders only while at least one secret is active (`JwtSettings.tsx:232`). If the list is empty, click "Generate New Secret" first (toast "New JWT secret generated successfully"; the previous state is not restorable, but a new secret does not end sessions, `:44,160-161`). Never click "Yes, Deactivate All Secrets": it deactivates every secret at once and signs everyone out, including the recorder (`:243-277`); click "Cancel" at the confirmation. Blur the secret ids and previews (`:186-190`). The voiceover wording follows the page text: "Generating a new secret will not invalidate existing tokens until they expire naturally." (`:160-161`) and "All users will need to log in again." (`:258`).
- Terms: JWT here is the authentication token the backend issues; it is not a flag token. Access tokens last 30 minutes and refresh tokens 7 days by default (`config.rs:156-163`); the script does not state those numbers.
- UI scenes run on the demo stack from video 02 or any running instance; the editor scenes show files that are never started on camera. Record the editor scenes first, then the browser scenes, and keep the browser on `admin`. Docker was not run to validate block A; if you start it for real, validate with `docker compose -f docker-compose.production.yml config` and use a throwaway database.
- Brief changes. The brief's `kubectl apply -k` and the 3-backend clustered setup are dropped (private repos, single backend instance). The brief's scene on TLS from a repo guide became a proxy-or-load-balancer line with no certificate on screen. Continuity row 16 now reads "Fresh production host ..." instead of "Fresh Kubernetes cluster." and its end state is "Production checklist covered; SSO configured; JWT emergency actions shown."
- State left behind: a sandbox SSO provider with one group mapping (delete it from the provider row if you do not want it kept), "Enforce single sign-on" off, JWT secrets unchanged unless one was generated for the take.
