# FluxGate demo video series

Produce narrative scripts for a series of short demo videos that cover FluxGate end to end, from first install to full Jira integration and TypeSafe Jev AI assistance, touching every user-facing UI screen in a logical order. Each video is embedded in the matching section of the FluxGate product website, so developers adopting FluxGate can follow along and configure their own instance.

## Chapters and website sections

| Chapter | Videos | Website section |
|---|---|---|
| 1 Get started | 01–03 | Get started |
| 2 Model your release | 04–07 | Model your release |
| 3 Connect your app | 08–09 | Connect your app |
| 4 Ship safely | 10–11 | Ship safely |
| 5 Integrations | 12–14 | Integrations |
| 6 Observe and operate | 15–16 | Observe and operate |

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

- Backend and CLI from branch `cli-followups` (or merge it to main first). It fixes the first-admin 401 bug and the CLI build.
- `FLUXGATE_ENCRYPTION_KEY` set (required for Jira write-back tokens and SSO secrets).
- `TYPESAFE_API_KEY` set; otherwise all AI UI stays hidden.
- Edge server running on 8081 with an edge client configured.
- Jira Cloud sandbox reachable by FluxGate's public Events URL (tunnel if running locally).
- Browser viewport 1440×900, light theme, zoom 100%, clean profile.
- A traffic generator (k6 script from `perf-test/` or `k6-tests/`) run before video 15 so dashboards have data.
- Each video lists its start state. Videos 2–14 build on each other; a seed snapshot after each chapter allows re-recording one video without redoing the chain.
- CLI binary (built with `cargo build -p fluxgate-cli` in `feature-toggle-cli-followups`): `feature-toggle-cli-followups/target/debug/fluxgate`. The binary name is `fluxgate`.
- Run `python3 docs/demo-videos/tools/check_script.py docs/demo-videos/*.md --cli-bin feature-toggle-cli-followups/target/debug/fluxgate --coverage` before recording.

## Before you publish

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

## Continuity

| Video | Start state | End state |
|---|---|---|
| 01 | Fresh: no install needed; concept video. | No data created. |
| 02 | Fresh machine with Docker. | FluxGate running (backend 8080, edge 8081, UI 3000); `admin` signed in; no team. |
| 03 | End of 02: `admin` signed in, no team. | Team `Checkout`; users `priya` (Requester) and `sam` (Approver) in `Checkout`; `priya` has set a permanent password. |
| 04 | End of 03: team and users exist. | Environments Development, Staging, Production; pipeline `checkout-release` (Dev → Staging → Production). |
| 05 | End of 04: environments and pipeline exist. | Contexts `country` (US, CA, UK) and `user_tier` (free, plus). |
| 06 | End of 05: contexts exist. | Feature `express-checkout` (CONTEXTUAL, kind Release, variants `classic` and `express`, pipeline `checkout-release`, no criteria); feature `holiday-banner` (SIMPLE). |
| 07 | End of 06: features exist without criteria. | `express-checkout` criteria on Development and Staging: CA + plus → `express` (priority 1), 20/80 `express`/`classic` split (priority 2); Development stage deployed; rollout template `plus-first-then-20` saved. |
| 08 | End of 07: Development stage deployed. | Clients `checkout-service` (Backend) and `juniper-web` (Web, origin `http://localhost:5173`) on Development; evaluations recorded. |
| 09 | End of 08: clients exist. | CLI signed in as `priya`; automation client `ci-bot` exists; config exported to `fluxgate-config.yaml`. |
| 10 | End of 09: no approval policy yet. | Policy `Release approvals` (All Environments, Approver role); `express-checkout` deployed to Staging after `sam` approved; Production request rejected by `sam` with comment "Ship Production through CHK-142 so QA sign-off is tracked." |
| 11 | End of 10: Staging deployed, Production rejected. | Freeze window `Holiday freeze` created then ended (no active freeze); `holiday-banner` emergency-disabled then re-enabled; one scheduled change on `holiday-banner` cancelled; `holiday-banner` restored from Version History. |
| 12 | End of 11: no active freeze. | Jira integration `Juniper Jira` with rules In Review → request Production, Approved → approve Production, Done → deploy Production; Jira Automation rule active; write-back connected. |
| 13 | End of 12: Jira integration ready. | `CHK-142` linked and Done; `express-checkout` deployed to Production; FluxGate comments on `CHK-142`. |
| 14 | End of 13: Production deployed. | All four AI toggles on; `Release approvals` AI risk mode "Require one extra approver when high"; flags classified; a `holiday-banner` Staging request with an AI risk assessment, approved. |
| 15 | End of 14 plus traffic generator run. | No changes. |
| 16 | Fresh Kubernetes cluster. | FluxGate on k8s production overlay with TLS and SSO configured. |

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
