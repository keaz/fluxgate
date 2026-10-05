# 09 · CLI and automation

| Field | Value |
|---|---|
| Website section | Connect your app › CLI and CI |
| Length target | 3:30 |
| Takeaway | You sign the `fluxgate` CLI in with a device code, gate a pipeline on a flag, create a `ci-bot` token and export your configuration. |
| Start state | End of 08: clients exist. |
| End state | CLI signed in as `priya`; automation client `ci-bot` exists; config exported to `fluxgate-config.yaml`. |
| Prerequisites | `fluxgate` on your `PATH` (built from `feature-toggle-cli-followups`, not from `main`); browser signed in as `priya`, with `admin` credentials ready for the System Clients scene; the demo stack from video 02 is running. |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Split terminal and browser on `/features`. | Flags are not only for the UI. You also want to read them in a terminal and gate a pipeline on them. The fluxgate CLI does both. In this video you sign it in, build a token for CI, export your configuration and watch live data. | |
| 0:15 | Terminal: run `fluxgate login --use-device-code`. It prints a link and a code. Browser: open `/device`; the page "Approve a CLI login" shows "The CLI will be signed in as" `priya` and the field "Code shown in the terminal". Type the code, click "Approve". The page shows "Approved". | Log in with the device code flow. The CLI prints a link and a short code, so it works over ssh or in a container where no browser can open. Open the link signed in as the person who should own the session, check that the code matches, and approve. Never approve a code you did not start. | Highlight the account name and the code |
| 0:40 | Terminal: run `fluxgate teams use Checkout`, `fluxgate configure set environment Development` and `fluxgate whoami`. | Login does not pick a team, so set one. Then set development as the default environment. Who am I confirms the account, the team and when the token expires. | Highlight the `team` row |
| 0:58 | Terminal: run `fluxgate flags list`, then `fluxgate flags get express-checkout`. | List the flags, then get one by key. Add the json flag when a script is reading the output. | Zoom on the table |
| 1:15 | Terminal: run the evaluate command from Code on screen, block A. The output shows `express`. | Evaluate asks the backend directly, so you can test a rule from a script without the edge server. The context is a JSON object, and the targeting key is required. | Highlight `--context` |
| 1:33 | Show block B in the editor: the CI gate. Terminal: run it and then `echo $?`. | For a pipeline, add the exit code flag. Zero means the flag is on, ten means off, and other codes are errors. It only works for boolean flags. Express-checkout returns a string, so the gate uses holiday-banner. Set the URL and token as environment variables, so nothing is stored on the build agent. | Highlight `--exit-code` |
| 2:06 | Log out, sign in as `admin`. Click "System Clients" under "Connect" to open `/system-clients`, click "Create System Client" to open `/system-clients/create`. Type `ci-bot` in "Name", leave "Expires At (UTC)" on its default, keep "Evaluate" selected under "Token Scope", click "Create System Client". The "Automation JWT Token" box shows the masked token; blur it. | A pipeline needs its own identity, not a person's login. That is a system client. Creating one takes an admin or a team admin, so sign in as admin. Name it ci-bot and keep the evaluate scope, which is all the gate needs. The token is shown only now, so copy it into your CI secret store. It expires after thirty days unless you change the date. | Highlight "Token Scope" |
| 2:42 | Terminal as `priya`: run `fluxgate config export --json > fluxgate-config.yaml`, then `fluxgate config import --file fluxgate-config.yaml --dry-run`. | Export writes the team, its environments and every flag to a file. Keep it as a backup or a starting point for another instance. Import creates the environments and flags a target is missing, and its dry run flag shows the changes first. Stages, variants and criteria are not imported. | Highlight `--dry-run` |
| 3:02 | Two terminals. Left: `fluxgate watch evaluation-summary`. Right: run curl block C from video 08 again. JSON lines appear on the left. | One more: watch follows a live stream, one JSON document per line. Run it, send some evaluations from the other terminal, and the summary updates. It suits dashboards and quick checks while you roll out. | Zoom on the JSON lines |
| 3:20 | Terminal with the prompt; browser on `/system-clients` listing `ci-bot`. | Your app, your terminal and your pipeline now read the same flags. Next, deploying to Staging and Production with approvals. | |

## Hand-off

Next: ship `express-checkout` safely with approvals, risk markers and rejection (video 10).

## Gotchas while recording

- CLI binary: build from `feature-toggle-cli-followups` (`target/debug/fluxgate`); `main` does not build from a fresh clone (README issue 3). Every command in this script was checked with `--help` against that binary: `login`, `teams use`, `configure set`, `whoami`, `flags list`, `flags get`, `evaluate`, `config export`, `config import`, `watch`.
- The brief names the button "Create Automation Client". The UI says "Create System Client" on `/system-clients` (`SystemClientsPage.tsx:33`) and on `/system-clients/create` (`SystemClientCreate.tsx:331,522`); the page title is "System Clients" and the nav item sits under "Connect". The placeholder "Automation Client" is only the example text in the name field (`:334`). The token box is "Automation JWT Token" (`:415`), and it says "It is shown only when created or regenerated."
- Who can create `ci-bot`: all `/system-clients` routes need a system admin or a `Team Admin` (`feature-toggle-backend/src/logic/policy.rs:282-310`; `priya` would get 403). Hence the account switch to `admin`. The CLI session stays `priya`'s. If you record in one take, do the `/device` step as `priya` first, then switch.
- `login` flags: `--use-device-code`, `--no-browser`, `--password`, `--sso`, `--url`, `--team`, `--env`. Output is `To log in, open <link> and enter the code <code>` (`fluxgate-cli/src/auth/device.rs:73`); the code looks like `BCDF-GHJK`; it polls for up to 10 minutes. `login` does not save `--team` or `--env` (`commands/login.rs` only writes `session` and `url`), so the script runs `fluxgate teams use Checkout` and `fluxgate configure set environment Development`. The brief put these on `login`; the code does not support that.
- `/device` page text (`DeviceLogin.tsx`): title "Approve a CLI login"; description "Approve only if you started fluxgate login on your own machine and the code matches."; line "The CLI will be signed in as" followed by the username; input labelled "Code shown in the terminal"; buttons "Approve" and "Deny"; outcome title "Approved" with the text "CLI login approved. You can close this tab and return to the terminal." If the browser is signed out the page shows "Sign in to continue" first. A link with `?code=` pre-fills the code.
- Brief change on `--exit-code`: the brief gates `express-checkout`. The CLI exits 2 with `--exit-code needs a boolean flag; 'express-checkout' returned express` for a non-boolean flag (`commands/evaluate.rs:30-42`; the exit code is 10 only when `value` is `false`, `error.rs:14`). `express-checkout` has string variants, so block B gates `holiday-banner` (SIMPLE, boolean). `holiday-banner` has no deployed stage at this point in the series, so its result was not verified. Run block B once before recording; if the CLI reports an error rather than exit 10, record only the `echo $?` for whichever code appears and trim the voiceover accordingly, or deploy `holiday-banner` to Development first.
- Exit codes (`fluxgate-cli/README.md`, Exit codes): 0 success, 1 other error, 2 usage or config, 3 auth, 4 forbidden, 5 not found, 6 conflict, 7 server or network, 10 flag off with `--exit-code`.
- `evaluate` flags: `--flag`, `--targeting-key`, `--context`, `--exit-code`, `--env`, `--json`. It takes `--flag`, not a positional key, and it calls the backend `/evaluate`, not the edge (`commands/evaluate.rs:13-24`). The edge variant is `fluxgate edge evaluate`; not used here.
- Environment in CI: with a token that has only the `Evaluate` scope the CLI cannot resolve an environment name (it lists environments, which needs `Admin read`), so block B uses `FLUXGATE_ENVIRONMENT_ID` with the Development environment's id (`context.rs:180-200`). The team comes from the token (a system-client token is bound to one team). `ci-bot`'s default scopes on the page are "Evaluate" and "Metrics write" (`SystemClientCreate.tsx:25`); the script keeps the defaults and mentions only evaluate.
- Token expiry default is 30 days (`SystemClientCreate.tsx:33-38`); "Expires At (UTC)" is required. The page navigates to `/system-clients/:id/edit` after create, where the token box still shows (state kept). Blur the token and never read it aloud.
- Brief change on `config export`: the command prints JSON (team, environments, features), not YAML (`commands/config_export.rs`). The continuity row names the file `fluxgate-config.yaml` and JSON is valid YAML, so the script keeps the name. `config import` creates missing environments and flags only; stages, variants and criteria are not imported (`fluxgate-cli/README.md`, Commands, Config). `--dry-run` shows what would be created.
- `watch` streams: `evaluation-summary`, `evaluation-rates`, `evaluations-by-feature`, `evaluation-dashboard`, `system-metrics`, `recent-activities`, `feature-growth`, `approval-requests`. Evaluation streams push when an evaluation is recorded (`feature-toggle-backend/src/rest/stream.rs:1103-1117`), and the first message arrives on connect. The brief says to watch while toggling in the UI. `approval-requests` would need a new approval request, which would break the start state of video 10 (no requests beyond Development), so the script drives the stream with evaluations instead. Use `--count 5` to end the command on its own. Not run live here (no stack).
- The CLI default URL is `http://localhost:8080/api/v1`, matching the demo stack, so no `FLUXGATE_URL` is needed for the interactive steps. Config lives in `~/.fluxgate/config`; do not show `~/.fluxgate/credentials`.

## Code on screen

Block A: evaluate against the backend (the context has the same attributes as video 08).

```bash
fluxgate evaluate --flag express-checkout --targeting-key user-1 --context '{"country":"CA","user_tier":"plus"}' --json
```

Block B: the CI gate. Exit 0 means on, 10 means off.

```bash
export FLUXGATE_URL=http://localhost:8080/api/v1
export FLUXGATE_TOKEN=<redacted>
export FLUXGATE_ENVIRONMENT_ID=<development environment id>

if fluxgate evaluate --flag holiday-banner --targeting-key ci --exit-code; then
  echo "banner on"
else
  echo "banner off, exit code $?"
fi
```

Block C is the evaluation loop from video 08 (block C there).
