# FluxGate demo video series

Produce narrative scripts for a series of short demo videos that cover FluxGate end to end, from first install to full Jira integration and TypeSafe Jev AI assistance, touching every user-facing UI screen in a logical order. Each video is embedded in the matching section of the FluxGate product website, so developers adopting FluxGate can follow along and configure their own instance.

## Chapters and website sections

| Chapter | Videos | Titles | Website section |
|---|---|---|---|
| 1 Get started | 01–03 | What is FluxGate; Install and first boot; Teams, users and roles | Get started |
| 2 Model your release | 04–07 | Environments and pipelines; Contexts; Create your first feature; Targeting rules | Model your release |
| 3 Connect your app | 08–09 | Clients and edge server; Automation and CI | Connect your app |
| 4 Ship safely | 10–11 | Approvals and policies; Safety nets | Ship safely |
| 5 Integrations | 12–14 | Jira setup; Jira end to end; Jev AI assistance | Integrations |
| 6 Observe and operate | 15–16 | Dashboards; Going to production | Observe and operate |

## Story bible

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

## Recording setup

- Public distribution: the source repositories are private, so viewers only get the Docker Hub images and the two files from the FluxGate docs. Record exactly what a viewer can do: no source checkout, no local image builds, no branch, and no command-line tool. The `fluxgate` CLI is not part of the public videos.
- Images: `keaz/flux-gate-backend:v1.2.0`, `keaz/flux-gate-edge:v1.2.0` and `keaz/flux-gate-ui:v1.2.0` (published on Docker Hub, multi-arch amd64 and arm64; `latest` is published too, and for backend and edge it is the same digest as `v1.2.0`). v1.2.0 includes the first-admin fix (no restart after "Create Admin"). Pull before recording and check the tag with `docker compose -f docker-compose.demo.yml images`.
- Demo stack: `docs/demo-videos/assets/docker-compose.demo.yml` (postgres, backend, ui; edge under profile `edge`) with `docs/demo-videos/assets/config.demo.toml`. Copy both files into an empty folder and record from there, so the paths on screen match what a viewer types. The compose file pins the three images to `v1.2.0`; there is no build option.
- Demo compose notes: the UI container has no proxy, so its `BACKEND_HOST` is `localhost` (the browser calls `${BACKEND_PROTOCOL}://${BACKEND_HOST}:${BACKEND_PORT}/api/v1` directly) and backend port 8080 is published; `EDGE_CLIENT_ID` and `EDGE_CLIENT_SECRET` default to empty so a plain `up -d` works before the edge profile is used.
- Settings live in a `.env` file next to the compose file; docker compose reads it automatically, so the values survive new terminals between videos. Video 02 writes `FLUXGATE_ENCRYPTION_KEY` there (required; encrypts Jira write-back tokens and SSO secrets, so never change it while the database lives).
- `TYPESAFE_API_KEY` is appended to `.env` before video 14, followed by `docker compose -f docker-compose.demo.yml up -d backend`; without it all AI UI stays hidden.
- Edge server on 8081 started in video 08 (`--profile edge up -d edge`) after `EDGE_CLIENT_ID` and `EDGE_CLIENT_SECRET` from a client created in the UI (its client ID and its API key) are appended to `.env`.
- Postgres data sits in the named volume `pgdata`: `down` and `up -d` keep it, `down -v` wipes it (use that only to reset the series).
- Jira Cloud sandbox reachable by FluxGate's public Events URL (tunnel such as cloudflared or ngrok if running locally).
- `curl` and `jq` for videos 08, 09 and 11; Node 20 or newer for video 08.
- Browser viewport 1440×900, light theme, zoom 100%, clean profile.
- Type all values live at a natural pace (no pasting or autofill), except secrets, which are pasted off camera or blurred.
- A traffic generator (internal recorder tool, not shown to viewers: a copy of the k6 load script adapted to `express-checkout` and `holiday-banner`, plus metric events; see video 15 Gotchas) run before video 15 so dashboards have data.
- Each video lists its start state. Videos 2–15 build on each other; a seed snapshot after each chapter allows re-recording one video without redoing the chain.
- Run `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/*.md --coverage` before recording.

## Before you publish

| # | Issue | Effect on series | Mitigation |
|---|---|---|---|
| 1 | Spring Boot starter uses the old edge contract, its OpenFeature provider coerces values to boolean, and it is only a `1.0.0-SNAPSHOT` that is not documented as published | Cannot demo Spring Boot | Video 8 uses curl, OFREP and the OpenFeature OFREP provider; the Spring Boot appendix is removed until the starter is fixed and published |
| 2 | First-admin bug: other workers return 401 until restart | Video 2 may fail live | Resolved in v1.2.0 (published; checked live on 2026-10-05: sign-in and API calls right after "Create Admin" work without a restart) |
| 3 | CLI did not build from a fresh clone | Video 9 was blocked | Resolved in v1.2.0; the CLI is also dropped from the public videos, so video 9 no longer uses it |
| 4 | Feature Rollout dashboard has hard-coded status (`FeatureRollout.tsx:103`) | Misleading on camera | Excluded from video 15 until fixed |
| 5 | Stale docs: root `ReadME.md` §7 and `FluxGate-System-Guide.md` (GraphQL) | Viewers following docs hit errors | Fix before publishing video 2 and 16 |
| 6 | A TLS private key and an edge client secret are committed | Must not appear on screen | Never show those files; rotate before publishing |
| 7 | No Jira `kill` action (JI-54 open) | Cannot demo "Jira closes → kill switch" | Script does not claim it |
| 8 | AI auto-approval can stall silently after transient DB errors | Video 14 auto-approve beat may misbehave | Use advisory and extra-approver modes on camera |
| 9 | Live coverage so far: the v1.2.0 images were smoke-tested on 2026-10-05 (compose up, `/docs/`, UI `config.js`, first admin and repeated sign-in, team, environment, pipeline and `holiday-banner` over REST, Backend client, edge `/health`, OFREP ETag 304, `ci-bot` evaluate, `gate.sh` exit 10, scope 403, data kept across `down` and `up -d`). Not run against real services: Jira Cloud (videos 12, 13), TypeSafe Jev (video 14), OIDC SSO (video 16); the UI flows were not clicked through in a browser | Those videos may differ from the script on first take | Do a dry run of videos 12–14 and 16 with the real services before recording |

## Continuity

| Video | Start state | End state |
|---|---|---|
| 01 | Fresh: no install needed; concept video. | No data created. |
| 02 | Fresh machine with Docker and the two demo files downloaded. | FluxGate running (backend 8080, UI 3000); edge server defined but not started (starts in 08); `admin` signed in; no team. |
| 03 | End of 02: `admin` signed in, no team. | Team `Checkout`; users `priya` (Requester) and `sam` (Approver) in `Checkout`; `priya` has set a permanent password. |
| 04 | End of 03: team and users exist. | Environments Development, Staging, Production; pipeline `checkout-release` (Dev → Staging → Production); approval policy `Release approvals` (All Environments, Approver role). |
| 05 | End of 04: environments and pipeline exist. | Contexts `country` (US, CA, UK) and `user_tier` (free, plus). |
| 06 | End of 05: contexts exist. | Feature `express-checkout` (CONTEXTUAL, kind Release, variants `classic` and `express`, pipeline `checkout-release`, no criteria); feature `holiday-banner` (SIMPLE). |
| 07 | End of 06: features exist without criteria. | `express-checkout` criteria on Development and Staging: CA + plus → `express` (priority 1), 20/80 `express`/`classic` split (priority 2); Development stage deployed after `sam` approved; rollout template `plus-first-then-20` saved. |
| 08 | End of 07: Development stage deployed. | Clients `checkout-service` (Backend) and `juniper-web` (Web, origin `http://localhost:5173`) on Development; evaluations recorded. |
| 09 | End of 08: clients exist. | System client `ci-bot` exists; its token is saved as `FLUXGATE_TOKEN` in the terminal; `gate.sh` exits with 10 for `holiday-banner`; signed in as `admin`. |
| 10 | End of 09: policy `Release approvals` exists (from 04); no approval requests beyond Development; signed in as `admin`. | Policy `Release approvals` reviewed; `express-checkout` deployed to Staging after `sam` approved; Production request rejected by `sam` with comment `Ship Production through CHK-142 so QA sign-off is tracked.` |
| 11 | End of 10: Staging deployed, Production rejected. | Freeze window `Holiday freeze` created then ended (no active freeze); `holiday-banner` Development stage deployed (approved by `sam`); `holiday-banner` emergency-disabled then re-enabled; one scheduled change on `holiday-banner` cancelled; `holiday-banner` restored from Version History. |
| 12 | End of 11: no active freeze. | Jira integration `Juniper Jira` with rules In Review → request Production, Approved → approve Production, Done → deploy Production; Jira Automation rule active; write-back connected. |
| 13 | End of 12: Jira integration ready. | `CHK-142` linked and Done; `express-checkout` deployed to Production; FluxGate comments on `CHK-142`. |
| 14 | End of 13: Production deployed. | All four AI toggles on; `Release approvals` AI risk mode "Require one extra approver when high"; flags classified; a `holiday-banner` Staging request with an AI risk assessment, approved. |
| 15 | End of 14 plus traffic generator run. | Metric `checkout_conversion` created; no other changes. |
| 16 | Fresh production host with Docker Hub access; FluxGate not yet installed there. | Production checklist covered; SSO configured; JWT emergency actions shown. |

## Script template

````markdown
# 07 · Targeting rules

| Field | Value |
|---|---|
| Website section | Model your release › Targeting |
| Length target | 4:00 |
| Takeaway | You can target Canadian Plus users first, then split everyone else 20/80. |
| Start state | End of 06: `express-checkout` exists with variants and pipeline, no criteria. |
| End state | Criteria saved on Development and Staging; Development stage deployed. |
| Prerequisites | Signed in as `priya`. |
| Label exceptions | "Priority 1" |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Feature list at `/features`. | You have a flag. Now decide who sees what. | |
| 0:10 | Click `express-checkout`, then "Edit". | ... | Zoom on stage graph |

## Hand-off

Next: connect a real app to the edge server and evaluate `express-checkout` (video 08).

## Gotchas while recording

- ...
````

Rules:

- `Label exceptions` is optional. Use it only for labels built at runtime (e.g. "Priority 1" from `Priority {n}`) and give the source line in a Gotchas bullet.
- `Start state` must begin with `End of NN` (previous video number, two digits) or with `Fresh`.
- `Length target` is `m:ss`.
- Extra sections (e.g. an appendix) may follow "Gotchas while recording".
- UI labels are written in straight double quotes exactly as the code renders them, e.g. "Create New Feature". Typed values, keys, routes and commands go in backticks. Never use double quotes for anything except UI labels.
- No `|` characters inside table cells except escaped as `\|`.
- Scripts refer to people by username or role, never by gendered pronoun.
- Never show or name committed secret files (TLS private key, edge client secret). Secrets on screen are shown as `<redacted>` or blurred.
- Speaking rate is 140 words per minute; length is 2–4 minutes per video.
