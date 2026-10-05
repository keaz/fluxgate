# 08 · Clients and edge server

| Field | Value |
|---|---|
| Website section | Connect your app › Edge server and SDKs |
| Length target | 4:00 |
| Takeaway | Your app evaluates `express-checkout` against the edge server with a client's SDK key, using curl, OFREP or the OpenFeature SDK. |
| Start state | End of 07: Development stage deployed. |
| End state | Clients `checkout-service` (Backend) and `juniper-web` (Web, origin `http://localhost:5173`) on Development; evaluations recorded. |
| Prerequisites | Signed in as `priya` with team `Checkout` selected; terminal in the folder from video 02 (it holds `docker-compose.demo.yml`), with `jq` and Node 20 or newer installed; the demo stack from video 02 is running (the edge server is not). |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Split screen: an editor with a small Node app on the left, a browser tab on `/clients` on the right. | Your app shouldn't call the admin backend on every flag check. It asks the edge server, a small service that keeps a cached copy of your flag configuration and answers from it. In this video you create the credentials, start the edge, and evaluate express-checkout three ways. | Caption: app asks the edge, not the backend |
| 0:20 | Click "Clients" under "Connect" to open `/clients`. Click "Create New Client" to open `/clients/create`. Type `checkout-service` in "Client Name", choose "Backend" in "Client Type", choose `Development` in "Environment", click "Create Client". | A client is how an app identifies itself. Start with the backend service: name it checkout-service, set the type to backend, and bind it to development. The environment decides which stage configuration the client sees, so a development client never receives production rules. | Highlight "Environment" |
| 0:50 | The page reloads on the edit page showing "API Key" and "SDK key", both masked; blur them. Click the copy button next to "API Key" and paste it into the terminal as `EDGE_CLIENT_SECRET`. Back on `/clients`, click the copy button in the "Client ID" column and paste it as `EDGE_CLIENT_ID`. Run the compose command from Code on screen, block A, then the health check. | The edge server needs an identity to reach the backend, so give it this client. Copy two things: the API key, which is the secret and is blurred here, and the client ID. The SDK key your apps use is the client ID, a dot, then the API key. Export both, then start the edge profile of the compose file. The health endpoint answers 200 once the edge connects. | Caption: copy client ID and API key; SDK key = ID + dot + key; blur the key |
| 1:30 | Back on `/clients`, click "Create New Client". Type `juniper-web` in "Client Name", choose "Web" in "Client Type". The "Web Origins" field appears; type `http://localhost:5173`. Choose `Development` in "Environment", click "Create Client". | Now the browser app. Choose web and the form asks for web origins. The edge answers a web client only when the request comes from an origin on this list, because browsers enforce cross-origin rules. Add localhost 5173, where the storefront runs. | Highlight "Web Origins" |
| 1:50 | Open `/developer/setup`, the "SDK Setup Wizard". Scroll to "Ready Snippets" and point at "Edge OFREP (SDK key)" and "REST Evaluate". | The setup wizard collects ready snippets. The edge OFREP one is a curl with your SDK key in the authorization header. The REST evaluate one calls the backend, and the next video uses it. | Highlight "Ready Snippets" |
| 2:05 | Terminal: run curl block B from Code on screen. The JSON response shows `express`. | First the plain evaluate endpoint. A Canadian Plus user asks for express-checkout. Always send a bucketing key, because the weighted rule uses it to place a user. The answer is express, from the first rule. This endpoint takes no credentials: it answers as the client the edge was started with, so keep port 8081 on a private network. | Highlight `bucketingKey` |
| 2:30 | Terminal: run loop block C. Output shows counts per variant. | Now twenty US free users. They skip the Canadian rule and land in the weighted split, so about one in five gets express. A given user id always gets the same answer. | Zoom on the counts |
| 2:45 | Terminal: run block D, then the second call with the ETag. The second response is `304 Not Modified`. | OpenFeature clients use the OFREP endpoints, which authenticate with the SDK key. The bulk call evaluates every flag in one request and returns an ETag. Send it back as if-none-match and the edge replies 304 with no body while the flags and the context are unchanged. | Highlight the `ETag` header and the 304 line |
| 3:10 | Open `/developer/integrations`, "OpenFeature & OFREP". Point at "Compatibility Matrix". | The integrations page lists OFREP compatibility and example calls. Its token details describe the backend's own endpoints. Your apps use the SDK key against the edge. | Highlight "Compatibility Matrix" |
| 3:22 | Editor: show `app.mjs` from Code on screen, block E. Terminal: `npm install`, then `node app.mjs`. | And the OpenFeature SDK. Install the server SDK and the OFREP provider, point the provider at the edge, and pass the SDK key as a header. Ask for the string value of express-checkout with a default of classic, and the same context. That is fifteen lines, and none of it is FluxGate specific. | Highlight the `baseUrl` line |
| 3:48 | Terminal prints `checkout: express`. Cut to `/clients` listing both clients. | Two clients, one edge server, and an app evaluating from it. Next, your pipeline: an identity of its own, and a gate on a flag. | |

## Hand-off

Next: give a CI pipeline its own identity and gate a job on a flag (video 09).

## Gotchas while recording

- Edge is not running at the start. The compose file defines it under profile `edge` and it needs `EDGE_CLIENT_ID` and `EDGE_CLIENT_SECRET` (`docs/demo-videos/assets/docker-compose.demo.yml`, service `edge`). Without both, the edge container cannot connect (the variables default to empty so that video 02's plain `up -d` works). The edge credentials are a normal client's UUID and API key (video 02 Gotchas), not an SDK key and not a System Client. The edge image is `keaz/flux-gate-edge:v1.2.0`. Run block A once before recording.
- Which client should the edge use? Use `checkout-service` (Backend). A Web client works too but then `POST /evaluate` demands an `Origin` header on every call (`feature-toggle/docs/edge-server-api.md`, CORS section, 403 without it), and the curl in block B sends none. The client must be bound to Development, because the edge evaluates in its own client's environment.
- Who authenticates what (`feature-toggle/docs/edge-server-api.md`, Authentication section): `POST /evaluate` takes no credentials and always evaluates as the edge-configured client (`checkout-service`, Development); `POST /ofrep/v1/evaluate/flags` and `POST /ofrep/v1/evaluate/flags/{key}` authenticate the caller by SDK key (`<clientId>.<apiKey>`) in `Authorization: Bearer` or `X-API-Key`, and evaluate in the caller's own environment. A mismatching `environment_id` in the context gives 401. A Web client SDK key needs an `Origin` on the allowed list, so the Node script and the curl use the Backend client's SDK key. Do not publish port 8081 to untrusted networks, since `/evaluate` is unauthenticated.
- Every example sends a bucketing key. `/evaluate` requires `context.bucketingKey` (`feature-edge-server/src/handlers.rs:27-31`); OFREP uses `targetingKey`. With the weighted criterion on Development an empty key makes the whole stage unmatched (`feature-toggle/evaluation-engine/src/lib.rs:506-520`). Development criteria: priority 0 is CA plus `user_tier` plus → `express`, priority 1 is the 20/80 `express`/`classic` split (video 07).
- Context attribute names are the context keys from video 05: `country` and `user_tier`. They are top-level fields next to `bucketingKey` or `targetingKey`.
- The brief says the API key is shown once. The UI shows it every time: `ClientCreate.tsx` loads `apiKey` into the edit page (`:60-62`, "API Key" block at `:321`), and `/clients` lists it in the "SDK key" column (`components/tables/ClientTable.tsx:101-104`). The voiceover therefore says the API key is the secret and does not say it appears once. The edge needs both the client ID and the API key (`EDGE_CLIENT_ID`, `EDGE_CLIENT_SECRET`), so the scene copies both. The copy buttons carry no visible text; the one next to "API Key" has `aria-label="Copy API key to clipboard"` (`ClientCreate.tsx:345`). The table header reads "Client ID"; the copy button is titled "Copy Client ID" (`ClientTable.tsx:22`).
- Labels: the create page title is "Create Client" and the button on `/clients` is "Create New Client" (`ClientsPage.tsx:33`). The "Web Origins" textarea is required for Web clients and appears only when the type is Web (`ClientCreate.tsx:171,302`). The navigation item "Clients" sits under the group "Connect" (`layout/navConfig.ts:85-88`). After "Create Client" the page navigates to `/clients/:id/edit` (`ClientCreate.tsx:150-153`).
- Client creation has no role check in the route policy (only `PATCH /clients/{id}` does, `feature-toggle-backend/src/logic/policy.rs:374`), so `priya` can create both clients. Do not click "Update Client" as `priya`.
- Setup wizard: header "SDK Setup Wizard"; card "Ready Snippets" with blocks "REST Evaluate", "Edge OFREP (SDK key)", "Spring Boot WebClient" and "FluxGate CLI" (`DeveloperSetupWizard.tsx:498-504`). "REST Evaluate" and "Spring Boot WebClient" use the backend `/evaluate` with a system-client token, not the edge. The "FluxGate CLI" block shows a command-line tool that is not part of this series: point only at the two blocks named in the scene and do not scroll slowly past the last two. The edge snippet shows `$FLUXGATE_EDGE_URL` and `$FLUXGATE_SDK_KEY` placeholders (`:219-222`).
- Integrations page: header "OpenFeature & OFREP"; "Compatibility Matrix", "Authentication" and "Examples" load from the backend (`fetchOfrepStatus`, `DeveloperIntegrationsPage.tsx`). Its text describes scoped tokens for the backend, which differs from the edge's SDK key auth; the voiceover says so. If the live status card shows an error, cut the scene.
- OpenFeature provider: package `@openfeature/ofrep-provider` 0.2.5 with `@openfeature/server-sdk` 1.23.0 (checked with `npm view`; the README documents `new OFREPProvider({ baseUrl, headers })`). The package's code requests `${baseUrl}/ofrep/v1/evaluate/flags/<key>`, so `baseUrl` is the edge root without a path. The README's `headers` object form is used. Use `setProviderAndWait` so the first evaluation does not race the provider start. The script is an ES module: save it as `app.mjs`, no `package.json` setting needed. The run itself was not executed here (no edge instance).
- Brief change: the brief says "second call returns 304". The API doc says the ETag covers the flag set, the client environment and the context, so repeat the call with the same context and the same SDK key, or it returns 200 again (`edge-server-api.md`, bulk endpoint).
- The 20/80 split is deterministic per bucketing key (SHA-256 of the stage bucket key and the key, `evaluation-engine/src/lib.rs:524-531`). With 20 user ids the count is near, not exactly, 4 express; read the counts on screen as they are. The voiceover says about one in five.
- Secrets: show the API key, SDK key and `EDGE_CLIENT_SECRET` blurred or as `<redacted>` and blur the terminal when you run block A and D. Never open the committed edge `config.toml` or key files.
- "evaluations recorded" in the end state: the edge reports evaluations to the backend. Check `/dashboard/evaluation-analytics` after recording; it is not shown in this video.
- Spring Boot appendix removed (public distribution): the starter is `io.github.keaz:fluxgate-spring-boot-starter` at `1.0.0-SNAPSHOT` (`fluxgate-springboot/pom.xml:14-16`, `fluxgate-springboot/README.md:23-27`). The README never says it is on Maven Central and a SNAPSHOT version is not a release, so viewers cannot depend on it; the appendix also described the old edge contract. Re-add it only after the starter is published and fixed.

## Code on screen

Block A: start the edge (the exports are typed, secrets blurred).

```bash
export EDGE_CLIENT_ID=<checkout-service client id>
export EDGE_CLIENT_SECRET=<redacted>
docker compose -f docker-compose.demo.yml --profile edge up -d edge
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8081/health
```

Block B: one evaluation as the edge client.

```bash
curl -s -X POST http://localhost:8081/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"flagKey":"express-checkout","context":{"bucketingKey":"user-1","country":"CA","user_tier":"plus"}}' | jq
```

Block C: twenty US free users.

```bash
for i in $(seq 1 20); do
  curl -s -X POST http://localhost:8081/evaluate \
    -H 'Content-Type: application/json' \
    -d "{\"flagKey\":\"express-checkout\",\"context\":{\"bucketingKey\":\"user-$i\",\"country\":\"US\",\"user_tier\":\"free\"}}" | jq -r .variant
done | sort | uniq -c
```

Block D: OFREP bulk, then the same call with the ETag from the first response.

```bash
export FLUXGATE_SDK_KEY=<redacted>
curl -si -X POST http://localhost:8081/ofrep/v1/evaluate/flags \
  -H "Authorization: Bearer $FLUXGATE_SDK_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"context":{"targetingKey":"user-1","country":"CA","user_tier":"plus"}}'
curl -si -X POST http://localhost:8081/ofrep/v1/evaluate/flags \
  -H "Authorization: Bearer $FLUXGATE_SDK_KEY" \
  -H 'If-None-Match: <etag value from the first response>' \
  -H 'Content-Type: application/json' \
  -d '{"context":{"targetingKey":"user-1","country":"CA","user_tier":"plus"}}'
```

Block E: `app.mjs` (run `npm install @openfeature/server-sdk @openfeature/ofrep-provider`, then `node app.mjs`).

```js
import { OpenFeature } from '@openfeature/server-sdk';
import { OFREPProvider } from '@openfeature/ofrep-provider';

await OpenFeature.setProviderAndWait(new OFREPProvider({
  baseUrl: 'http://localhost:8081',
  headers: { Authorization: `Bearer ${process.env.FLUXGATE_SDK_KEY}` },
}));

const client = OpenFeature.getClient();
const variant = await client.getStringValue('express-checkout', 'classic', {
  targetingKey: 'user-1',
  country: 'CA',
  user_tier: 'plus',
});
console.log(`checkout: ${variant}`);
await OpenFeature.close();
```
