# 09 · Automation and CI

| Field | Value |
|---|---|
| Website section | Connect your app › Automation and CI |
| Length target | 3:30 |
| Takeaway | A CI job can ask FluxGate whether a flag is on with its own scoped token and one REST call, and fail the build when the flag is off. |
| Start state | End of 08: clients exist. |
| End state | System client `ci-bot` exists; its token is saved as `FLUXGATE_TOKEN` in the terminal; `gate.sh` exits with 10 for `holiday-banner`; signed in as `admin`. |
| Prerequisites | `admin` credentials ready (the System Clients page needs an admin or a team admin); `curl` and `jq` installed; the demo stack from video 02 is running; team `Checkout` selected in "Select team". |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Terminal and browser side by side. Browser: avatar menu, click "Log out"; sign in as `admin` with team `Checkout` selected; speed this up. | A deploy pipeline has no one to click a button. Before it ships, it may need to know whether a flag is on. That takes an identity of its own and an endpoint to call. In this video you create both, then gate a job on a flag. | Time-lapse for the sign-in |
| 0:22 | Click "System Clients" under "Connect" to open `/system-clients`, click "Create System Client" to open `/system-clients/create`. Type `ci-bot` in "Name", leave "Expires At (UTC)" on its default, keep "Evaluate" selected under "Token Scope", click "Create System Client". The "Automation JWT Token" box shows the masked token; blur it. Copy it. | A pipeline needs its own identity, not a person's login. That is a system client. Creating one takes an admin or a team admin, so you are signed in as admin. Name it ci-bot and keep the default scopes, because the gate only needs evaluate. The token is shown only now, so copy it into your CI secret store. It expires after thirty days unless you change the date. | Highlight "Token Scope"; blur the token |
| 0:58 | Browser at `http://localhost:8080/docs/`. Expand `POST /api/v1/evaluate` under the `Evaluation` tag; point at the request body fields and the 200 response. | Now the endpoint. The backend serves its own API docs in Swagger. Under evaluation, a post to evaluate takes a feature key, an environment ID, a targeting key and an optional context. The token already names your team, so you send no team ID. The answer carries a value, a variant and a reason. | Highlight `featureKey`, `environmentId`, `targetingKey` |
| 1:28 | Open `/developer/setup`, the "SDK Setup Wizard". Choose `Development` in "Environment", type `holiday-banner` in "Feature Key". In "Ready Snippets", the "REST Evaluate" block shows the request with the real environment ID; copy that ID. | The request needs the environment ID. The setup wizard fills it in. Pick development and the flag, and the REST evaluate snippet shows the request with the real ID. Copy it. Holiday-banner is a plain on or off flag, so it makes the simplest gate. | Highlight `environmentId` in the snippet |
| 1:52 | Editor: show `gate.sh` from Code on screen, block A. Terminal: type the three exports from block B, secrets blurred. | This is the whole gate. Curl posts the request with the token as a bearer header, and jq reads the value field. If it is true, the script prints banner on. Otherwise it exits with ten, and the CI job fails. If curl itself fails, for a bad token or a wrong key, the script stops with that error, so a broken gate never looks like an off flag. Keep the URL and token in environment variables. | Highlight `exit 10` |
| 2:34 | Terminal: run `bash gate.sh; echo $?` from block B. It prints `banner off` and `10`. | Run it. Nothing has deployed holiday-banner yet, so its Development stage is off. The evaluation answers false, and the script exits with ten. That is a failed gate, with nobody watching. | Zoom on `10` |
| 2:56 | Terminal: run the request from block C. The response shows status 403 and the code `system_client_scope_violation`. | One more property. This token only carries the evaluate and metrics scopes. Try to create a feature with it and the backend answers 403, with a scope violation. A leaked CI token can ask about flags, but it cannot change them. | Highlight `403` |
| 3:16 | Browser on `/system-clients` listing `ci-bot`. | Your pipeline now asks FluxGate before it ships. Next, deploying to Staging and Production with approvals. | |

## Hand-off

Next: ship `express-checkout` safely with approvals, the blast radius and a rejection (video 10).

## Gotchas while recording

- The brief calls the button "Create Automation Client". The UI says "Create System Client" on `/system-clients` (`SystemClientsPage.tsx:33`) and on `/system-clients/create` (`SystemClientCreate.tsx:296,522`); the nav item "System Clients" sits under "Connect". The placeholder "Automation Client" is only the example text in the name field (`:334`). The token box is "Automation JWT Token" (`:440`), and it says "It is shown only when created or regenerated."
- Public distribution: this video no longer uses the `fluxgate` command-line tool or the `/device` login page. The CLI is not part of the public series, and the old scenes (device-code login, `flags list`, `config export`, `watch`) are gone. The scenes that remain are the system client, Swagger and a curl plus jq gate against the backend REST API.
- Who can create `ci-bot`: all `/system-clients` routes need a system admin or a `Team Admin` (`feature-toggle-backend/src/logic/policy.rs:282-310`; `priya` would get 403). Hence the first scene signs in as `admin`, with team `Checkout` selected. The setup wizard also needs the team selected (`DeveloperSetupWizard.tsx:61`), so check the team selector before 1:28.
- The endpoint, in code: `POST /api/v1/evaluate` (`feature-toggle-backend/src/rest/evaluation.rs:276-290`), tagged `Evaluation` (`:287`). Body, camelCase (`:12-21`): `teamId` optional, `featureKey`, `environmentId`, `targetingKey`, `context` (object, default empty). `featureKey`, `environmentId` and `targetingKey` must be non-empty (400 `featureKey is required`, `environmentId is required`, `targetingKey is required`, `:313-320`); an unknown key gives 404 `feature not found` (`:328`). The team comes from the token when it has one (`:302`), because the guard sets `team_id: Some(claim_team_id)` for a system client token (`middleware/jwt_guard.rs:798`); `teamId` is only needed for a user token without a team. Response (`:23-31`, `:343-350`): `flagKey`, `value`, `variant`, `reason`, `errorCode`.
- Auth: a header `Authorization: Bearer <token>` (`middleware/jwt_guard.rs:365-367`). The path is under `/api/v1`, and the demo UI's REST base URL is `http://localhost:8080/api/v1` (entrypoint, `feature-toggle-ui/docker-entrypoint.sh:14`). The scope rule: a system client token may `POST /api/v1/evaluate` only with the `evaluate` scope (`jwt_guard.rs:212-214`). `ci-bot`'s default scopes on the page are "Evaluate" and "Metrics write" (`SystemClientCreate.tsx:25`), and the UI sends that pair explicitly. The backend default, used only when a request omits `scopes`, is all four: `evaluate`, `metrics:write`, `admin:read` and `flag:write` (`logic/system_client.rs:21-28`), so a client created through the REST API without `scopes` can write flags. The script keeps the page defaults and mentions only evaluate and metrics. Checked live on v1.2.0: a client created with `scopes` `evaluate` and `metrics:write` got a token with exactly those two.
- Why 403 in scene 2:56: a `POST` on a path containing `features` needs the `flag:write` scope (`jwt_guard.rs:237-241`); without it the guard returns 403 `System client token scope does not allow this operation` with `"code": "system_client_scope_violation"` (`jwt_guard.rs:132-138,700-704`). The check runs before routing and before any validation, so the empty body `{}` in block C creates nothing. Checked live on v1.2.0: block C printed `HTTP/1.1 403 Forbidden` and the body `{"code":"system_client_scope_violation","details":null,"error":"forbidden","message":"System client token scope does not allow this operation"}`.
- Swagger: `/docs/` with a trailing slash. The route is registered as `/docs/{_:.*}` (`rest/mod.rs:769`) and `utoipa-swagger-ui` 9.0.2 `actix.rs` adds no redirect from `/docs`, so `http://localhost:8080/docs` without the slash returns 404 (checked live on v1.2.0; `/docs/` returns 200). Swagger UI shows the `Authorization` header parameter on this operation (`rest/mod.rs:644-658`). The Swagger page itself has no FluxGate labels, so the script quotes none of its buttons.
- Environment ID source: the wizard's "REST Evaluate" snippet carries `environmentId` from the "Environment" select (`DeveloperSetupWizard.tsx:179-183`, select at `:361-374`), and the "Feature Key" input fills `featureKey`. The snippet shows `teamId` too; the gate drops it because the token has the team. The snippet text appears only after you choose an environment; the page picks the first environment automatically (`:116-119`), so make sure it reads `Development`, not the first in the list. Blur nothing here: an environment ID is not a secret.
- Why `holiday-banner`: `express-checkout` returns strings, so a boolean gate would have to compare `.value` to `express`; `holiday-banner` is SIMPLE, boolean. Verified outcome of block B (exit 10): stages of a new flag are created with `enabled: false` (`feature-toggle-backend/src/logic/feature.rs:653`) and become enabled only on deployment (`database/feature.rs:3155`). `holiday-banner` is not deployed before video 11, so the engine returns `value: false`, reason `DISABLED` (`feature-toggle/evaluation-engine/src/lib.rs:817-826`), with HTTP 200, and the script maps `false` to exit 10. A missing stage or a disabled kill switch also gives `false`. Record 09 before 11; after 11 the flag is deployed and the gate answers differently. Checked live on v1.2.0 with `holiday-banner` NOT_DEPLOYED on Development: `POST /api/v1/evaluate` answered 200 with `value` false and reason `DISABLED`, and block B printed `banner off` and `10`.
- Exit codes of the script: 0 on, 10 off (the script's own `exit 10`). `curl -f` turns any HTTP 4xx or 5xx into curl's exit 22 and `set -o pipefail` carries it out of the pipe, so a bad token (401), a wrong scope (403) or a typo in the key (404) stops the job with 22, not 10 (checked live: an unknown key gave exit 22). Say nothing more about exit codes on camera than the voiceover does.
- Token expiry default is 30 days (`SystemClientCreate.tsx:35-40`); "Expires At (UTC)" is required. The page navigates to `/system-clients/:id/edit` after create, where the token box still shows (state kept). Blur the token and never read it aloud. Video 11 reuses `gate.sh` and the exported variables, so keep the terminal session or save the three exports.
- Dropped on purpose: configuration export and live updates. There is no REST endpoint for a full configuration export (the closest are per-feature routes and the bulk feature action `export` in `rest/feature.rs:864`, which is a UI list action, not a backup), and no UI page streams live updates in this scene; the old versions of those beats used the CLI. README continuity row 09 records the new end state.
- Secrets: the token is shown only as `<redacted>`; blur the "Automation JWT Token" box, and the `export FLUXGATE_TOKEN` line.

## Code on screen

Block A: `gate.sh`. Exit 0 means the flag is on, 10 means off.

```bash
#!/usr/bin/env bash
# CI gate: exit 0 when holiday-banner is on, 10 when it is off.
set -euo pipefail

value=$(curl -sf -X POST "$FLUXGATE_URL/evaluate" \
  -H "Authorization: Bearer $FLUXGATE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"featureKey\":\"holiday-banner\",\"environmentId\":\"$FLUXGATE_ENVIRONMENT_ID\",\"targetingKey\":\"ci\"}" \
  | jq -r .value)

if [ "$value" = "true" ]; then
  echo "banner on"
else
  echo "banner off"
  exit 10
fi
```

Block B: the exports (secrets blurred), then run the gate.

```bash
export FLUXGATE_URL=http://localhost:8080/api/v1
export FLUXGATE_TOKEN=<redacted>
export FLUXGATE_ENVIRONMENT_ID=<development environment id>

bash gate.sh; echo $?
```

Block C: the token cannot write.

```bash
curl -si -X POST "$FLUXGATE_URL/features" \
  -H "Authorization: Bearer $FLUXGATE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'
```
