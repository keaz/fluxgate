# 01 · What is FluxGate

| Field | Value |
|---|---|
| Website section | Get started › Overview |
| Length target | 2:00 |
| Takeaway | FluxGate separates deploying code from releasing a feature, and a few services make that work. |
| Start state | Fresh: no install needed; concept video. |
| End state | No data created. |
| Prerequisites | None. Optionally a running instance for the sidebar tour. |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Title card, then a simple split: a deploy arrow on the left, a release switch on the right. | Deploying code and releasing a feature are two different events. When they are the same event, every release is a deploy and every rollback is a redeploy. FluxGate lets you separate them. | Title card: FluxGate |
| 0:15 | Architecture diagram `media/system_overview.jpg`. | Here is how the pieces fit. You work in the UI. The UI talks to the backend, which serves REST on port 8080 and gRPC on port 50051, and keeps everything in Postgres. Your applications do not call the backend. They call the edge server on port 8081. | Highlight UI, then backend, then Postgres in turn |
| 0:36 | Same diagram, highlight the edge server and the gRPC link. | The edge server holds a cached copy of the feature set, streamed from the backend over gRPC. It answers evaluations from that cache, so your apps get fast answers close to where they run. | Highlight edge server and gRPC arrow |
| 0:52 | Browser at `/dashboard/overview`, signed in. Hover the sidebar from the top. | Open the UI and the sidebar has five groups. "Observe" holds the dashboards: evaluations, metrics and audit activity. | Highlight the "Observe" group |
| 1:01 | Hover "Build". | "Build" is where you model a release: features, pipelines, contexts and environments. | Highlight the "Build" group |
| 1:07 | Hover "Connect". | "Connect" covers the clients that evaluate flags, and integrations. | Highlight the "Connect" group |
| 1:12 | Hover "Govern". | "Govern" is approvals, approval policies and freeze windows, the controls that keep a release safe. | Highlight the "Govern" group |
| 1:19 | Hover "Settings". | "Settings" holds teams, users, roles and the rest of the admin setup. | Highlight the "Settings" group |
| 1:25 | Slow zoom out on the overview, then fade to a Juniper Market title card with the text `express-checkout`. | Through this series you follow Juniper Market, an online grocery. The Checkout team wants to ship a one-tap flow called `express-checkout`: Plus users in Canada first, then a gradual split for everyone else, with a second person approving each step. | Title card: Juniper Market, `express-checkout` |
| 1:43 | Terminal window, empty prompt. | First, get FluxGate running on your own machine. That is the next video. |  |

## Hand-off

Next: install FluxGate with Docker Compose and create the first admin (video 02).

## Gotchas while recording

- Use the system overview image `media/system_overview.jpg` for the architecture scene; `media/system_overview_2.jpg` is an alternative. Confirm the diagram matches the ports named in the voiceover (8080 REST, 50051 gRPC, 8081 edge) before recording; redraw if it differs.
- Sidebar group labels come from `feature-toggle-ui/src/layout/navConfig.ts` lines 62-130 (Observe, Build, Connect, Govern, Settings). The "Settings" group only appears for users with team management access, so record the tour as `admin`.
- Do not click into "Feature Rollout" under "Observe"; it shows hard-coded status and is excluded from the series.
- The tour needs a running instance. Record it after video 02, or reuse the instance from video 02; no data is created on screen.
- Run the sidebar tour in one steady pass with the pointer moving top to bottom; do not open any pages.
