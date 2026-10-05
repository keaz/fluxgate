# FluxGate Demo Video Series — Design

Date: 2026-10-05
Status: Draft for review

## 1. Goal

Produce narrative scripts for a series of short demo videos that cover FluxGate end to end — from first install to full Jira integration and TypeSafe Jev AI assistance — touching every user-facing UI screen in a logical order. Each video is embedded in the matching section of the FluxGate product website, so developers adopting FluxGate can follow along and configure their own instance.

### Success criteria

- Every routed UI screen that works today appears in at least one video (see §7 coverage matrix).
- A developer who watches videos 1–15 in order can reproduce the full setup on their own instance.
- Each video stands alone: it states its start state, recaps in one line, and hands off to the next video.
- Every UI label in a script matches the current UI code exactly.
- Each script fits its length target at ~140 spoken words per minute.

### Decisions made during brainstorming

| Topic | Decision |
|---|---|
| Production format | Screen recording with voiceover |
| Length | 2–4 minutes per video, 16 videos (15 core + 1 optional) |
| Ordering | Dependency journey: what must exist first comes first |
| Continuity | One continuous storyline across all videos |
| Deliverable | Markdown in this repo under `docs/demo-videos/` |
| SDK coverage | curl, OFREP, OpenFeature OFREP provider, and the CLI. The Spring Boot starter is scripted as a separate segment marked "record after starter fix". |

### Out of scope

- Recording, editing, or automating the videos.
- Code changes to FluxGate. Blockers that affect recording are listed in §6 so they can be fixed separately.
- Website copy outside the videos.

## 2. Storyline bible

**Company:** Juniper Market, a fictional online grocery.
**Team:** Checkout.
**Hero feature:** `express-checkout` — a one-tap checkout flow.
- Feature type: CONTEXTUAL. Kind: release.
- Variants: `classic` (String) and `express` (String).
- Owner: `priya`. Tags: `checkout`, `q4`.
- Ticket / Reference URL: Jira issue `CHK-142`.

**Supporting feature:** `holiday-banner` — a SIMPLE flag used for the kill-switch and scheduled-change demos (video 11) and the flag-kind classification demo (video 14).

**Cast** (shown by username only; scripts refer to people by role):

| Username | Role in story | FluxGate role |
|---|---|---|
| `admin` | Platform admin | System admin |
| `priya` | Checkout developer | Requester |
| `sam` | Release manager | Approver |

**Environments:** Development, Staging, Production (types Development / Staging / Production).
**Pipeline:** `checkout-release` with stages Dev → Staging → Production.
**Contexts:** `country` (values `US`, `CA`, `UK`) and `user_tier` (values `free`, `plus`).
**Clients:** `juniper-web` (Web, origin `http://localhost:5173`) and `checkout-service` (Backend).
**Jira:** Jira Cloud sandbox, project key `CHK`, workflow To Do → In Review → Approved → Done.

**Story arc:** The Checkout team wants to roll out express checkout safely: Plus users in Canada first, then a 20/80 split for everyone else, gated by approvals, driven from Jira, with Jev flagging risky changes.

## 3. Series outline

Website chapters map 1:1 to product-site sections.

### Chapter 1 — Get started

**01 What is FluxGate** (~2 min)
- Hook: shipping code and releasing features are different events.
- Architecture diagram: UI, backend (REST 8080, gRPC 50051), edge server (8081), Postgres.
- Quick tour of the sidebar groups: Observe, Build, Connect, Govern, Settings.
- Introduce Juniper Market and `express-checkout`.

**02 Install and first boot** (~3 min)
- `docker compose up` with backend, UI, Postgres; edge server added from `feature-toggle/docker-compose.yml`.
- `config.toml` essentials: `allowed_origin`, `http_addr`, `grpc_addr`, `public_base_url`.
- Env vars: `DATABASE_URL`, `FLUXGATE_ENCRYPTION_KEY` (`openssl rand -base64 32`), optional `TYPESAFE_API_KEY`.
- Migrations run on startup. Swagger at `/docs`.
- `/create-admin` → "Create Admin Account" → "Create Admin" → `/login` → "Sign in".

**03 Teams, users, roles** (~3 min)
- Settings → Teams → "Create New Team" → `Checkout`.
- Settings → Users → "Create User" for `priya` and `sam`: Team Assignment, Role Assignment, "Set Temporary Password".
- Settings → Roles: "Global Roles" (Approver, Requester, Team Admin).
- First login as `priya` shows "Update Your Password".
- 20-second mention: Single sign-on (OIDC, group mappings), Notifications.

### Chapter 2 — Model your release

**04 Environments and pipelines** (~3 min)
- Environments → "Create New Environment" modal ×3.
- Pipelines → "Create New Pipeline" → "Design your release workflow" → "Pipeline Stages", one stage per environment.
- Why pipelines: promotion order is enforced.

**05 Contexts** (~2 min)
- Contexts → create `country` and `user_tier` with "Add Value".
- How contexts become rule conditions and how the app sends them at evaluation time.

**06 Create your first feature** (~4 min)
- Features → "Create New Feature".
- Basic Information: Name, Description, Purpose, Ticket / Reference URL, Feature Type, Kind, Lifecycle, Owner, Expiry, Tags.
- "Feature Variants" → "Add Variant" → `classic`, `express`.
- "Pipeline Template" → `checkout-release`; stages render as a graph.
- "Blast Radius" panel.
- Feature list: status badges, Saved Views, View Details.

**07 Targeting rules** (~4 min)
- Edit Feature → click Staging stage → "Stage Editor".
- "Add Criterion": compound rule `country = CA AND user_tier = plus` → Specific Variant `express`.
- Second criterion: "Weighted Traffic Split" 20/80 express/classic.
- Drag to reorder; "Priority N"; lower number evaluates first.
- "Save Stage Criteria".
- "Rollout Templates": "Save Current As Template", "Apply Template".

### Chapter 3 — Connect your app

**08 Clients and the edge server** (~4 min)
- Clients → "Create Client" → `checkout-service` (Backend) and `juniper-web` (Web with origin). Copy SDK key `<clientId>.<apiKey>`.
- Developer → "SDK Setup Wizard": Create Scoped Token, Ready Snippets.
- curl `POST :8081/evaluate` with `{flagKey, context:{bucketingKey, country, user_tier}}` — show CA/plus gets `express`.
- OFREP: `POST /ofrep/v1/evaluate/flags` bulk with ETag/304.
- Integrations page: "OpenFeature & OFREP"; wire a standard OpenFeature OFREP provider in a small Node app.
- Separate segment (record later): Spring Boot starter, marked "record after starter fix".

**09 CLI and automation** (~3 min)
- `fluxgate login --use-device-code` → approve at `/device` ("Approve a CLI login").
- `fluxgate flags list`, `flags get express-checkout`, `flags search`.
- CI gate: `fluxgate evaluate express-checkout --exit-code` (exit 10 = off) with `FLUXGATE_URL` / `FLUXGATE_TOKEN`.
- System Clients → "Create Automation Client" → Token Scope → "Automation JWT Token".
- `fluxgate config export` / `config import` for environment-as-code.
- `fluxgate watch` streams live events.

### Chapter 4 — Ship safely

**10 Approvals and policies** (~4 min)
- Approval Policies → "Create Policy": Scope "Production Environments Only", Approver Roles, "Auto-approve After (hours)".
- As `priya`: Edit Feature → Production stage → "Actions" → "Request Deployment" with Reason and External Reference; policy preview banner.
- Header pending-approvals badge.
- As `sam`: Approvals → Pending → detail: Blast radius, Dependency impact, Structured diff, Approval policy, Status timeline, Votes → "Approve with comment".
- As `priya`: "Deploy".

**11 Safety nets** (~3 min)
- Freeze Windows → "New Window"; "Active change freeze" banner; Override Reason.
- `holiday-banner`: row action "Emergency Disable" (icon) → "Disable immediately"; "Kill switch ready" badge; EMERGENCY OVERRIDE badge.
- "Scheduled Changes": Action, Requested Status, Run At.
- Edit Feature → History tab → "Version History" → diff → rollback.
- Feature Detail tabs: Overview, Stages, Variants, Dependencies, Activity.

### Chapter 5 — Integrations

**12 Jira setup** (~4 min)
- Settings → Jira → "New integration": name, base URL, environment field, aliases, "Jira approves in".
- Connection: Events URL and secret (shown once), "Rotate secret".
- In Jira: Automation rule "Work item transitioned" → Send web request with `Bearer <secret>`. Alternative: native webhook with HMAC `X-Hub-Signature`.
- Status rules → "Add rule": In Review → `request` Staging; Approved → `approve` Production; Done → `deploy` Production.
- Write-back: Jira Cloud API token, "Post comments", test connection.

**13 Jira end-to-end** (~4 min, split screen)
- Feature Detail → Jira card → "Add Jira issue" → `CHK-142`.
- Move `CHK-142` to In Review → FluxGate creates a deployment request.
- Move to Approved → request approved (Jira-approved environment).
- Move to Done → Production deploy.
- Jira shows FluxGate comments and a remote link back to the feature.
- Settings → Jira → Event log and Outbound jobs; `fluxgate jira events` in terminal.
- Boundary statement: FluxGate does not transition Jira issues; Jira drives FluxGate.

**14 Jev AI assistance** (~4 min)
- Settings → "AI assistance" ("TypeSafe Jev judgments per team"): enable Approval risk triage, Reason quality check, Flag kind classification, Natural-language search.
- Request with a vague reason ("fix") → reason quality hint.
- Approvals detail → "AI risk assessment" panel (low/medium/high with reasons; includes Jira issue key).
- Approval Policies → "AI risk mode": Advisory, Block auto-approve when high, Require one extra approver when high.
- "Classify existing flags" → AI-suggested kind on `holiday-banner`.
- ⌘K → "Ask FluxGate": "which checkout flags are on in production for Canada?"
- Fail-open: when Jev is unavailable, approvals proceed without AI.

### Chapter 6 — Observe and operate

**15 Dashboards** (~3 min, after traffic generator runs)
- "System Overview": Total Features, Evaluations Today, Active Clients, System Success Rate; Activity Feed.
- Evaluation Analytics: Evaluation Timeline, Evaluations By Feature.
- "Metrics & Experiments": Variant Comparison `classic` vs `express`.
- Audit Analytics: Top Changed Flags, Actors, Recent Audit Events.
- ⌘K command palette quick links.

**16 Going to production** (optional, ~3 min, ops audience)
- `kubectl apply -k k8s/overlays/production`: 3 backends, clustering.
- TLS setup.
- Settings → "Single sign-on": OIDC provider, group-to-role mappings, enforce SSO.
- Settings → "JWT Secret Management" → Emergency Actions.

## 4. Script format

### Files

- `docs/demo-videos/README.md`
  - Series overview and chapter-to-website-section map.
  - Storyline bible (§2).
  - Recording setup (§5).
  - Continuity checklist: start state and end state of every video.
- `docs/demo-videos/NN-slug.md` — one script per video, e.g. `01-what-is-fluxgate.md`.

### Per-video layout

1. Header block: title, website section, length target, audience takeaway (one sentence), start state, end state, prerequisites.
2. Scene table with columns:
   - **Time** — cumulative timecode.
   - **On screen** — route, exact clicks, typed values, using real UI labels in quotes.
   - **Voiceover** — spoken text.
   - **Callout** — optional on-screen text, zoom, or highlight.
3. Closing hand-off line to the next video.
4. "Gotchas while recording" list.

### Voice and tone

- Second person, developer to developer, present tense.
- Open with a 10-second hook that names the problem the video solves.
- One line of *why* before each *how*, then show.
- No marketing superlatives. No claims about features that do not exist.
- ~140 words per minute; word count checks the length target.

## 5. Recording setup

- Backend and CLI from branch `cli-followups` (or merge it to main first). It fixes the first-admin 401 bug and the CLI build.
- `FLUXGATE_ENCRYPTION_KEY` set (required for Jira write-back tokens and SSO secrets).
- `TYPESAFE_API_KEY` set; otherwise all AI UI stays hidden.
- Edge server running on 8081 with an edge client configured.
- Jira Cloud sandbox reachable by FluxGate's public Events URL (tunnel if running locally).
- Browser viewport 1440×900, light theme, zoom 100%, clean profile.
- A traffic generator (k6 script from `perf-test/` or `k6-tests/`) run before video 15 so dashboards have data.
- Each video lists its start state. Videos 2–14 build on each other; a seed snapshot after each chapter allows re-recording one video without redoing the chain.

## 6. Known blockers and risks

| # | Issue | Effect on series | Mitigation |
|---|---|---|---|
| 1 | Spring Boot starter uses the old edge contract and its OpenFeature provider coerces values to boolean | Cannot demo Spring Boot today | Video 8 uses curl, OFREP, OpenFeature OFREP provider; Spring Boot segment recorded after fix |
| 2 | First-admin bug on main: other workers return 401 until restart | Video 2 may fail live | Record from `cli-followups` |
| 3 | CLI on main does not build from a fresh clone (`output.rs` ignored) | Video 9 blocked on main | Record from `cli-followups` |
| 4 | Feature Rollout dashboard has hard-coded status (`FeatureRollout.tsx:103`) | Misleading on camera | Excluded from video 15 until fixed |
| 5 | Stale docs: root `ReadME.md` §7, `FluxGate-System-Guide.md` (GraphQL), k8s edge env names, k8s missing encryption and TypeSafe env | Viewers following docs hit errors | Fix before publishing video 2 and 16 |
| 6 | A TLS private key and an edge client secret are committed | Must not appear on screen | Never show those files; rotate before publishing |
| 7 | No Jira `kill` action (JI-54 open) | Cannot demo "Jira closes → kill switch" | Script does not claim it |
| 8 | AI auto-approval can stall silently after transient DB errors | Video 14 auto-approve beat may misbehave | Use advisory and extra-approver modes on camera |

## 7. Screen coverage matrix

| Screen / route | Video |
|---|---|
| `/create-admin`, `/login` | 02 |
| `/temporary-password-reset` | 03 |
| `/settings/teams`, `/settings/users`, `/users/create`, `/settings/roles` | 03 |
| `/settings/notifications` | 03 (mention) |
| `/environments` + Create Environment modal | 04 |
| `/pipelines`, `/pipelines/create` | 04 |
| `/contexts`, `/contexts/create` | 05 |
| `/features`, `/features/create` | 06 |
| `/features/:id/edit` — Stage Editor, Rollout Templates | 07 |
| `/clients`, `/clients/create` | 08 |
| `/developer/setup`, `/developer/integrations` | 08 |
| `/device` | 09 |
| `/system-clients` | 09 |
| `/settings/approval-policies` | 10, 14 |
| `/approvals` | 10, 13, 14 |
| `/settings/freeze-windows` | 11 |
| `/features/:id` — Emergency modal, tabs, History | 11 |
| `/features/:id` — Jira card | 13 |
| `/settings/jira` | 12, 13 |
| `/settings/ai` | 14 |
| ⌘K command palette, "Ask FluxGate" | 14, 15 |
| `/dashboard/overview`, `/dashboard/evaluation-analytics`, `/dashboard/metrics`, `/dashboard/audit-analytics` | 15 |
| `/features/:id/edit` — Experiment tab | 15 |
| `/settings/sso`, `/settings/jwt` | 16 (mention in 03) |
| `/reset-password` | 03 (mention) |
| `/dashboard/rollout` | Excluded (blocker 4) |

## 8. Production approach for the scripts

- Draft scripts chapter by chapter.
- Verify every quoted UI label and route against `feature-toggle-ui/src` before marking a script done.
- Verify every CLI command and API path against `feature-toggle-cli-followups/fluxgate-cli` and backend routes.
- Check each script's word count against its length target.
