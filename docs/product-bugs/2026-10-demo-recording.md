# Product bugs found while recording the demo videos (October 2026)

These bugs were found during the dry runs and the recording of the FluxGate demo videos
(`docs/demo-videos/`, videos 02 to 15). The stack ran the published images
`keaz/flux-gate-*:v1.2.0`. Every bug below was checked against the source code. Line
references point to the current `main` branches: backend `keaz/feature-toggle` at `60deda7`,
UI `keaz/feature-toggle-ui` at `a3d4d6f`.

Story data used in the steps: team **Checkout**; users **admin** (system admin),
**priya** (Requester), **sam** (Approver); environments **Development**, **Staging**,
**Production**; pipeline **checkout-release**; features **express-checkout** and
**holiday-banner**; approval policy **Release approvals** (All Environments, Approver role,
1 required); system client **ci-bot**.

Each bug is filed as a GitHub issue (2026-10-06); none duplicated an existing issue.
UI bugs are in `keaz/feature-toggle-ui`, backend bugs in `keaz/feature-toggle`. Three
candidates were dropped after checking the code: the "Request Rollback" approval banner
after Deploy (intended preview), lingering toasts (a hidden-tab timer artifact of the
recording) and the metric toast quote style (docs wording only).

## Overview

| ID | Title | Repo | Severity | Issue |
|----|-------|------|----------|-------|
| B01 | Header team selector does not show a new team until the page is reloaded | UI | low | [keaz/feature-toggle-ui#4](https://github.com/keaz/feature-toggle-ui/issues/4) |
| B02 | Pipeline editor places new stages off-canvas and overlaps a second child stage | UI | medium | [keaz/feature-toggle-ui#5](https://github.com/keaz/feature-toggle-ui/issues/5) |
| B03 | Delete buttons on the Features and Pipelines lists do nothing | UI | medium | [keaz/feature-toggle-ui#6](https://github.com/keaz/feature-toggle-ui/issues/6) |
| B04 | Specific Variant criterion summary reads "0% allocated (100% open)" | UI | low | [keaz/feature-toggle-ui#7](https://github.com/keaz/feature-toggle-ui/issues/7) |
| B05 | Mouse wheel over the stage graph zooms the graph instead of scrolling the page | UI | low | [keaz/feature-toggle-ui#8](https://github.com/keaz/feature-toggle-ui/issues/8) |
| B06 | Approver roles show as raw id prefix ("Role 00000000") instead of role name | UI | low | [keaz/feature-toggle-ui#9](https://github.com/keaz/feature-toggle-ui/issues/9) |
| B07 | System client token is shown unmasked by default after create or regenerate | UI (private) | medium | [keaz/feature-toggle-ui#10](https://github.com/keaz/feature-toggle-ui/issues/10) |
| B08 | SDK Setup Wizard refills the Feature Key field as soon as it is cleared | UI | low | [keaz/feature-toggle-ui#11](https://github.com/keaz/feature-toggle-ui/issues/11) |
| B09 | Freeze Windows Scope column shows an environment id prefix instead of the name | UI | low | [keaz/feature-toggle-ui#12](https://github.com/keaz/feature-toggle-ui/issues/12) |
| B10 | Every stage deployment request is tagged "Production impact", even Staging | Backend | medium | [keaz/feature-toggle#19](https://github.com/keaz/feature-toggle/issues/19) |
| B11 | Version rollback uses window.confirm and silently confirms archiving | UI | medium | [keaz/feature-toggle-ui#13](https://github.com/keaz/feature-toggle-ui/issues/13) |
| B12 | Emergency dialog says "Approval required" but the kill switch skips approval | Backend | medium | [keaz/feature-toggle#20](https://github.com/keaz/feature-toggle/issues/20) |
| B13 | Approvals page shows user UUIDs and a feature id prefix instead of names | UI | medium | [keaz/feature-toggle-ui#14](https://github.com/keaz/feature-toggle-ui/issues/14) |
| B14 | "User added to team" activity description contains the raw user UUID | Backend | low | [keaz/feature-toggle#21](https://github.com/keaz/feature-toggle/issues/21) |
| B15 | System Clients and SDK Setup links shown to users without the Team Admin role | UI | low | [keaz/feature-toggle-ui#15](https://github.com/keaz/feature-toggle-ui/issues/15) |
| B16 | Pipelines list "Description" column shows the Active/Disabled status | UI | low | [keaz/feature-toggle-ui#16](https://github.com/keaz/feature-toggle-ui/issues/16) |
| B17 | SDK Setup Wizard shows the raw error code `team_admin_role_required` | UI | low | [keaz/feature-toggle-ui#17](https://github.com/keaz/feature-toggle-ui/issues/17) |
| B18 | A role assigned to the signed-in user has no effect until the next sign-in | UI | low | not filed |

## B01: Header team selector does not show a new team until the page is reloaded

Issue: [keaz/feature-toggle-ui#4](https://github.com/keaz/feature-toggle-ui/issues/4)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 03 (Teams, users, roles), dry run 02-05

**Steps to reproduce**

1. On a fresh install, sign in as `admin`. The header team selector reads "Select team".
2. Open Settings > Teams and create the team `Checkout`. The toast "Team created successfully" appears and the Teams table lists Checkout.
3. Open the header team selector.

**Expected:** The selector lists Checkout (and selects it when it is the only team).

**Actual:** The selector still reads "Select team" and has no entries. Checkout appears only after a full page reload.

**Root cause:** `TeamProvider` loads the team list once on mount and exposes no way to refresh it (`src/contexts/TeamContext.tsx:25-50`; the context value at line 91 has only `teams`, `selectedTeam`, `setSelectedTeam`). `CreateTeamModal` calls `createTeam` and then only `onCreated` (`src/components/modals/CreateTeamModal.tsx:54-58`), and `TeamsPage` reloads its own table only (`src/pages/TeamsPage.tsx:124-128`). The header reads the stale context list (`src/layout/Header.tsx:35`, `81`).

**Suggested fix:** Add a `refreshTeams()` function to `TeamContext` and call it after a team is created, renamed or deleted (and after team membership changes for the current user).

## B02: Pipeline editor places new stages off-canvas and overlaps a second child stage

Issue: [keaz/feature-toggle-ui#5](https://github.com/keaz/feature-toggle-ui/issues/5)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** medium
- **Where seen:** video 04 (Environments and pipelines), dry run 02-05

**Steps to reproduce**

1. Sign in as `admin` with team Checkout selected. Open Pipelines > Create Pipeline.
2. Enter the name `checkout-release`. Set the first stage to Development.
3. Click "+" under the first stage and set the new stage to Staging.
4. Click "+" under the Staging stage.
5. Nothing seems to happen, so click "+" under the Staging stage again.
6. Pick environments and click Save.

**Expected:** Each new stage is placed in view (the canvas pans or fits to show it). A second click either adds the next stage in the chain or is clearly visible as a branch. Save succeeds or gives an error that explains the problem.

**Actual:** The third stage is placed 200 px to the right of its parent, outside the visible canvas, so the first click looks like it failed. The second click adds a fourth stage as a second child of Staging, placed on top of the third stage, so it looks like a duplicate stage and edge. In the dry run the save then failed with "Failed to Create Pipeline / Pipeline must have at least 2 relationships". The workaround was to click once and drag the canvas to find the new stage.

**Root cause**

- `PipelineCreate` renders `PipelineFlow` without `fitViewKey` (`src/pages/PipelineCreate.tsx:274-281`). `PipelineFlow` fits the view only when `fitViewKey` is set (`src/components/PipelineFlow.tsx:215-220`); the `fitView` prop at line 237 applies only on first render.
- `addStage` always places a child at `parent.x + 200` (`src/components/PipelineFlow.tsx:96-110`). For a second child it uses `offsetY = 50 * (siblingCount - 1)`, which is `0`, and moves the existing sibling up by only 50 px (`src/components/PipelineFlow.tsx:133-145`), so the two nodes overlap.
- The backend check compares the relationship count for equality with `stages - 1` but the message says "at least" (`feature-toggle-backend/src/validation.rs:13-17`), so the error does not tell the user what is wrong. The exact click sequence that produced the relationship-count mismatch in the dry run was not isolated.

**Suggested fix:** Pass a `fitViewKey` (for example the node count) from `PipelineCreate`, or call `fitView` after `addStage`. Disable or hide "+" on a stage that already has a child unless branching is supported, and spread siblings so they never overlap. Make the backend message say "exactly N relationships (a linear chain)".

## B03: Delete buttons on the Features and Pipelines lists do nothing

Issue: [keaz/feature-toggle-ui#6](https://github.com/keaz/feature-toggle-ui/issues/6)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** medium
- **Where seen:** video 06 (Create your first feature), dry run 06-07

**Steps to reproduce**

1. Sign in as `admin` with team Checkout selected. Open Features.
2. Click the red trash button on the `express-checkout` row.
3. Open Pipelines and click the trash button on the `checkout-release` row.

**Expected:** A confirmation dialog, then the item is deleted or archived. If deletion is not supported, the button is not shown.

**Actual:** Nothing happens. No dialog, no request, no toast.

**Root cause:** Both pages pass a placeholder handler: `src/pages/FeatureListPage.tsx:10-13` and `src/pages/PipelinePage.tsx:10-13` (`// Placeholder for delete behavior ...; void env;`). The tables render the button and call it (`src/components/features/FeatureTable.tsx:814-820`, `src/components/tables/PipelineTable.tsx:97-103`). The backend has no `DELETE /features/{id}` or `DELETE /pipelines/{id}` route; features can only be archived (bulk action `archive`, `src/api/features.ts:198`).

**Suggested fix:** For features, wire the button to the existing archive action with a confirmation dialog (as `ContextsPage` does with `ConfirmationDialog`), or remove the button. For pipelines, remove the button until a delete endpoint exists.

## B04: Specific Variant criterion summary reads "0% allocated (100% open)"

Issue: [keaz/feature-toggle-ui#7](https://github.com/keaz/feature-toggle-ui/issues/7)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 07 (Targeting rules), dry run 06-07

**Steps to reproduce**

1. Sign in as `priya`. Open `express-checkout` > edit, Stages tab, select the Development stage.
2. Add a criterion. Set Variant Selection Mode to "Specific Variant" and pick `express`.
3. Add the rule group `country Equals CA AND user_tier equals plus` and collapse the criterion.

**Expected:** The criterion summary says which variant is returned, for example "Returns express".

**Actual:** The summary reads "0% allocated (100% open)", which suggests that the criterion serves no traffic.

**Root cause:** The summary line always uses the weighted-split total (`src/pages/FeatureCreate.tsx:244-246`, `293-298`). In Specific Variant mode `variantAllocations` is empty, so the total is 0. The mode is stored in `row.variantSelectionMode` and `row.selectedVariantControl` (`src/pages/FeatureCreate.tsx:327-331`), which the summary ignores.

**Suggested fix:** When `row.variantSelectionMode === 'SPECIFIC_VARIANT'`, show "Returns `<selectedVariantControl>`" instead of the allocation text.

## B05: Mouse wheel over the stage graph zooms the graph instead of scrolling the page

Issue: [keaz/feature-toggle-ui#8](https://github.com/keaz/feature-toggle-ui/issues/8)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 07 (Targeting rules), also videos 10, 11 and 14; dry run 06-07

**Steps to reproduce**

1. Sign in as `priya`. Open `express-checkout` > edit, Stages tab.
2. Put the pointer over the stage graph and scroll the mouse wheel to reach the criteria below.

**Expected:** The page scrolls. Zoom uses the graph controls, pinch, or a modifier key.

**Actual:** The graph zooms in or out and the page does not scroll. The same happens in the pipeline editor.

**Root cause:** `PipelineFlow` uses the React Flow defaults (`zoomOnScroll` and `preventScrolling` are both true) (`src/components/PipelineFlow.tsx:225-238`). The graph is embedded in a long form, so the wheel is captured.

**Suggested fix:** Set `zoomOnScroll={false}` and `preventScrolling={false}` (optionally `panOnScroll`) on `<ReactFlow>`, and add `<Controls />` for zoom.

## B06: Approver roles show as raw id prefix ("Role 00000000") instead of role name

Issue: [keaz/feature-toggle-ui#9](https://github.com/keaz/feature-toggle-ui/issues/9)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** videos 04, 07 (policy banner on the Stages tab), 10 (Approvals routing details), 11 (emergency disable/enable dialogs); dry runs 06-07 and 10-11

**Steps to reproduce**

1. Create the approval policy `Release approvals` with approver role `Approver`.
2. Sign in as `priya`, open `express-checkout` > edit, Stages tab, select the Staging stage.
3. Look at the approval policy banner. Then open Approvals, open a request and expand "Approval routing".

**Expected:** The approver role is shown by name: "Approver".

**Actual:** The banner shows a chip "Role 00000000". The routing details show "00000000". The seeded Approver role id is `00000000-0000-0000-0000-000000000001`, so every built-in role shows the same prefix.

**Root cause:** `ApprovalPolicyPreviewBanner` prints `Role {shortId(roleId)}` (`src/components/features/ApprovalPolicyPreviewBanner.tsx:131-139`). `ApprovalsPage` prints `roleId.slice(0, 8)` (`src/pages/ApprovalsPage.tsx:1136-1140`). `GET /api/v1/roles` is readable by any signed-in user (`feature-toggle-backend/src/rest/role.rs:68`) but the UI does not use it here.

**Suggested fix:** Load roles once (`fetchRoles`, `src/api/roles.ts:11`) and map role ids to names in both places. Alternatively include `approverRoles: [{id, name}]` in the policy summary returned by the API.

## B07: System client token is shown unmasked by default after create or regenerate

Issue: [keaz/feature-toggle-ui#10](https://github.com/keaz/feature-toggle-ui/issues/10)

- **Repo:** UI (`keaz/feature-toggle-ui`, private)
- **Severity:** medium
- **Security relevant:** yes. Keep this issue in the private UI repository.
- **Where seen:** video 09 (Automation and CI), dry run 08-09

**Steps to reproduce**

1. Sign in as `admin`. Open System Clients and create `ci-bot` with scopes `evaluate` and `metrics:write`.
2. Click "Create Scoped Token" (or regenerate a token).
3. Scroll down to the "Automation JWT Token" panel.

**Expected:** The new token is masked by default, like the client API key on the Clients page. The user reveals it with the eye button or copies it with the copy button.

**Actual:** The full token is shown in clear text as soon as it is created. It sits below the fold, so the user may not notice it is visible while the screen is shared or recorded.

**Root cause:** `SystemClientCreate` sets `setShowToken(true)` after every create and regenerate (`src/pages/SystemClientCreate.tsx:202`, `225`, `260`). The textarea renders the token when `showToken` is true (`src/pages/SystemClientCreate.tsx:454-459`). The Clients page starts masked (`src/pages/ClientCreate.tsx:23`).

**Suggested fix:** Keep `showToken` false after create and regenerate. Scroll the token panel into view and keep the copy button as the main action.

## B08: SDK Setup Wizard refills the Feature Key field as soon as it is cleared

Issue: [keaz/feature-toggle-ui#11](https://github.com/keaz/feature-toggle-ui/issues/11)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 09 (Automation and CI), dry run 08-09. Reported first as "Feature Key resets when other fields change"; the source shows it happens every time the field becomes empty, so it is deterministic, not intermittent.

**Steps to reproduce**

1. Sign in as `admin` with team Checkout selected. Open Integrations > SDK Setup Wizard.
2. The Feature Key field is prefilled with `express-checkout`.
3. Select the text and press Backspace to clear it, then start typing `holiday-banner`.

**Expected:** The field stays empty after it is cleared, so the user can type a new key.

**Actual:** The field is refilled with `express-checkout` as soon as it becomes empty. Typing a new key works only if the old text is replaced in one keystroke (select all, then type).

**Root cause:** An effect sets the key to the first feature whenever the key is empty (`src/pages/DeveloperSetupWizard.tsx:121-125`). Clearing the input sets `featureKey` to `''` (`src/pages/DeveloperSetupWizard.tsx:381-382`), which triggers the effect again.

**Suggested fix:** Prefill only once, for example with a `useRef` flag or only when no `featureKey` search param and no user edit exist.

## B09: Freeze Windows Scope column shows an environment id prefix instead of the name

Issue: [keaz/feature-toggle-ui#12](https://github.com/keaz/feature-toggle-ui/issues/12)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 11 (Safety nets), dry run 10-11

**Steps to reproduce**

1. Sign in as `admin`. Open Govern > Freeze Windows.
2. Create the freeze window `Holiday freeze` with Scope `Production`.
3. Look at the Scope column in the list.

**Expected:** The Scope column shows "Production".

**Actual:** The Scope column shows the first 8 characters of the Production environment id in monospace (for example `a557b0cb`).

**Root cause:** `src/pages/FreezeWindowsPage.tsx:297-298` renders `window.environmentId.slice(0, 8)`. The page already loads the team environments (`environmentsQuery`, `src/pages/FreezeWindowsPage.tsx:64`).

**Suggested fix:** Look up the environment name from `environmentsQuery.items` and fall back to the id prefix only when the environment is not found.

## B10: Every stage deployment request is tagged "Production impact", even Staging

Issue: [keaz/feature-toggle#19](https://github.com/keaz/feature-toggle/issues/19)

- **Repo:** Backend (`keaz/feature-toggle`)
- **Severity:** medium
- **Where seen:** video 10 (Approvals and policies), also video 14; dry run 10-11

**Steps to reproduce**

1. Use the policy `Release approvals` (Applies to: All Environments).
2. Sign in as `priya`. Open `express-checkout` > edit, Stages tab, select Staging, click "Request Deployment" with external reference `CHK-142`.
3. Sign in as `sam` and open the request on the Approvals page.

**Expected:** A Staging request has no "Production impact" marker. The marker appears only when the target environment is a production environment (or the policy is `production_only`).

**Actual:** The request shows the warning badge "Production impact". Approvers see the same marker on every stage request, so the marker loses its meaning.

**Root cause:** `entry_risk_markers` adds `production-impact` when the policy is `production_only` OR when any `status` diff entry has an after-value containing `DEPLOY` or `ROLLBACK` (`feature-toggle-backend/src/rest/approval.rs:580-617`, condition at `606-616`). Every stage request changes status to `DEPLOYMENT_REQUESTED`, so the marker is always added. The environment type is not checked. A related check in `logic/approval.rs:1161-1176` compares `stage.position` with `"production"`, which is not an environment attribute either.

**Suggested fix:** Pass the target environment (its `environment_type`) into `entry_risk_markers` and add `production-impact` only when the environment is a production environment or the policy is `production_only`.

## B11: Version rollback uses window.confirm and silently confirms archiving

Issue: [keaz/feature-toggle-ui#13](https://github.com/keaz/feature-toggle-ui/issues/13)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** medium
- **Where seen:** video 11 (Safety nets), dry run 10-11

**Steps to reproduce**

1. Sign in as `admin`. Open `holiday-banner` > History.
2. Select Version 2 and click Rollback.

**Expected:** An in-app confirmation dialog that names the version and lists what will change. If the target version has the lifecycle stage `archived`, the dialog says that the rollback archives the feature and asks for that confirmation explicitly.

**Actual:** A native browser dialog "Rollback feature to version 2?" appears. It cannot show details, can be suppressed by the browser, and blocks automation. The request always sends `archiveConfirmation: true`, so a rollback to an archived version archives the feature without telling the user.

**Root cause:** `src/components/features/FeatureHistoryPanel.tsx:155-160` calls `window.confirm`, then `rollbackFeatureVersion(featureId, selectedVersion.id, true)` at line 164. The backend requires that confirmation only when the restored version is archived (`feature-toggle-backend/src/database/feature.rs:4359`), which the UI bypasses. The same native pattern is used for bulk archive (`src/components/features/FeatureTable.tsx:552`) and bulk admin changes (`src/components/tables/UsersTable.tsx:225`).

**Suggested fix:** Use the existing `ConfirmationDialog` component. Pass `archiveConfirmation: true` only after the user confirms an archive explicitly.

## B12: Emergency dialog says "Approval required" but the kill switch skips approval

Issue: [keaz/feature-toggle#20](https://github.com/keaz/feature-toggle/issues/20)

- **Repo:** Backend (`keaz/feature-toggle`); the UI dialog also needs a small change
- **Severity:** medium
- **Where seen:** video 11 (Safety nets), dry run 10-11

**Steps to reproduce**

1. Use the policy `Release approvals` (All Environments, Approver role, 1 required).
2. Sign in as `admin`. Open `holiday-banner` and click "Emergency disable".
3. Read the banner in the dialog, enter a reason and confirm.
4. Open Approvals.

**Expected:** The dialog says that an emergency override applies at once without approval (and is limited to admins and Team Admins).

**Actual:** The dialog shows "Approval required" with the policy name and approver count. After confirming, the feature is disabled at once and no approval request exists. The same happens for "Emergency enable".

**Root cause:** The preview endpoint accepts `changeType: "emergency_action"` but then evaluates it as a normal stage change: `preview_approval_policy` calls `preview_stage_change_policy(team, environment, requested_status)` regardless of the change type (`feature-toggle-backend/src/rest/approval.rs:987-1036`, call at `1016`). The emergency handler applies the change directly after a role check, with no approval step (`feature-toggle-backend/src/rest/feature.rs:70-79`, `1798-1840`). The UI asks for this preview and renders it (`feature-toggle-ui/src/components/modals/FeatureEmergencyActionModal.tsx:126-130`, `234-241`).

**Suggested fix:** For `emergency_action`, return outcome `not_required` with a reason such as "Emergency overrides apply immediately and bypass approval policies". Alternatively stop rendering the policy banner in the emergency dialog and show a fixed notice instead.

## B13: Approvals page shows user UUIDs and a feature id prefix instead of names

Issue: [keaz/feature-toggle-ui#14](https://github.com/keaz/feature-toggle-ui/issues/14)

- **Repo:** UI (`keaz/feature-toggle-ui`); a backend change may be the cleaner fix
- **Severity:** medium
- **Where seen:** videos 07, 10 and 13 (approval cards and details), dry runs 10-11 and 12-13

**Steps to reproduce**

1. Sign in as `priya` and request a Development deployment of `express-checkout`.
2. Sign in as `sam`, open Approvals and approve the request with a comment.
3. Look at the request card and open its details.

**Expected:** The card shows the feature key (`express-checkout`). The details show "Requested by priya", "Approved by sam", and approver names in the routing section.

**Actual:** The card shows "Feature: 290348ac..." (feature id prefix). The details show "Feature <full UUID>", "Requested by <user UUID>", "Approved by <user UUID>", and 8-character id prefixes for explicit and eligible approvers.

**Root cause:** The UI renders the raw ids: `src/pages/ApprovalsPage.tsx:778` (feature id prefix), `902-903` (feature id, requested by), `620` (timeline hint), `1150-1154` and `1183-1187` (approver id prefixes), `1243` (`vote.approverId`). The API returns ids only: `ApprovalRequestResponse` has `feature_id`, `requested_by` and `eligible_approver_ids`, and `ApprovalVoteResponse` has `approver_id`, with no names (`feature-toggle-backend/src/rest/approval.rs:109-118`, `211-224`). The backend already resolves usernames for notifications (`logic/approval.rs:1297`).

**Suggested fix:** Add `featureKey`, `requestedByUsername`, `approverUsername` (per vote) and approver names to the approval request response, and render them in the UI. A UI-only fix can resolve names through `GET /users?teamId=...` and the team feature list.

## B14: "User added to team" activity description contains the raw user UUID

Issue: [keaz/feature-toggle#21](https://github.com/keaz/feature-toggle/issues/21)

- **Repo:** Backend (`keaz/feature-toggle`)
- **Severity:** low
- **Where seen:** video 15 (Dashboards, System Overview "Recent Activity"); the entries are created in video 03

**Steps to reproduce**

1. Sign in as `admin`. Create the user `priya` and assign her to the team `Checkout`.
2. Open the System Overview (`/dashboard/overview`) and look at Recent Activity.

**Expected:** "User priya was added to team Checkout".

**Actual:** "User '033f8a7d-...' added to team" (the full user UUID).

**Root cause:** The activity log description uses the user id, while the notification message built a few lines earlier uses the username: `feature-toggle-backend/src/logic/user.rs:654` (`format!("User '{}' added to team", id)`, compare lines 642-646) and `feature-toggle-backend/src/logic/user_tx.rs:296` (`format!("User '{}' added to team", user_id)`).

**Suggested fix:** Use the username and team name in both descriptions, for example `format!("User '{username}' added to team '{team_name}'")`, and keep the ids in `metadata`.

## B15: System Clients and SDK Setup links shown to users without the Team Admin role

Issue: [keaz/feature-toggle-ui#15](https://github.com/keaz/feature-toggle-ui/issues/15)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 08 (Clients and edge server), dry run 08-09

**Steps to reproduce**

1. Sign in as `priya` (Requester, team Checkout, no Team Admin role).
2. Look at the sidebar group "03 / Connect" and open System Clients, then Integrations > SDK Setup Wizard.

**Expected:** Links to pages that need the Team Admin role are hidden (or shown as read-only with an explanation) for users without that role.

**Actual:** System Clients and Integrations are shown. System Clients fails to load, and the SDK Setup Wizard shows an error box (see B17).

**Root cause:** The nav items have no gate (`src/layout/navConfig.ts:88-90`), while the backend requires Team Admin or system admin for every `system-clients` route (`feature-toggle-backend/src/logic/policy.rs:281-309`, decision at `479-497`). Environments and Clients are readable by all team members, so showing those two links is correct.

**Suggested fix:** Add `gate: 'teamsManagement'` to the System Clients item, and hide the system-client part of the SDK Setup Wizard for users who cannot manage system clients.

## B16: Pipelines list "Description" column shows the Active/Disabled status

Issue: [keaz/feature-toggle-ui#16](https://github.com/keaz/feature-toggle-ui/issues/16)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 04 (Environments and pipelines)

**Steps to reproduce**

1. Sign in as `admin`. Create the pipeline `checkout-release`.
2. Open Pipelines.

**Expected:** The column header matches its content: "Status" with Active/Disabled (pipelines have no description field).

**Actual:** The column is labelled "Description" and shows "Active".

**Root cause:** `src/components/tables/PipelineTable.tsx:82-87` defines `header: 'Description'` with `accessor: pipeline.active ? "Active" : "Disabled"`. The `Pipeline` type has no description.

**Suggested fix:** Rename the column to "Status" and render a status badge.

## B17: SDK Setup Wizard shows the raw error code `team_admin_role_required`

Issue: [keaz/feature-toggle-ui#17](https://github.com/keaz/feature-toggle-ui/issues/17)

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** video 08 (Clients and edge server), dry run 08-09

**Steps to reproduce**

1. Sign in as `priya` (no Team Admin role).
2. Open Integrations > SDK Setup Wizard.

**Expected:** A readable message, for example "Only Team Admins can create system clients and tokens. Ask a Team Admin, or continue with an existing token."

**Actual:** A red box under the system client selector shows `team_admin_role_required`.

**Root cause:** The wizard stores `err.message` from `fetchSystemClients` and renders it as is (`src/pages/DeveloperSetupWizard.tsx:94-103`, `344-347`). The backend policy guard sends the policy reason code as `message` (`feature-toggle-backend/src/middleware/jwt_guard.rs:141-147`, reason from `logic/policy.rs:497`). The same request also adds a "Policy deny" row to Recent Activity each time priya opens the wizard.

**Suggested fix:** Map 403 responses with `code: "policy_denied"` to readable text in the UI (a small reason-to-message table), and skip the system-client request for users who cannot manage system clients (see B15).

## B18: A role assigned to the signed-in user has no effect until the next sign-in

Issue: not filed

- **Repo:** UI (`keaz/feature-toggle-ui`)
- **Severity:** low
- **Where seen:** developer guide end-to-end run (docs site, Task 14)

**Steps to reproduce**

1. Sign in as `admin` (system admin without the Requester role).
2. Open Users, edit `admin`, go to **Assign Roles**, tick **Requester**, click **Assign Selected Roles**. The toast "Roles assigned successfully" appears.
3. Open a feature, select a stage and open **Actions**.

**Expected:** The new role applies at once, so **Actions** offers **Request Deployment**.

**Actual:** **Actions** shows only the hint "Requester role required to make requests". The role works only after logging out and signing in again.

**Root cause:** The UI reads roles from the decoded JWT in local storage (`src/utils/auth.ts:81-122`, `canRequestStageChange` calls `hasRole(ROLES.REQUESTER)`). Assigning roles does not refresh the token, and the hint text comes from `src/pages/FeatureCreate.tsx:2029`.

**Suggested fix:** After a successful role or team assignment to the current user, refresh the token (or show a notice such as "Sign out and in again to apply your new role").

## Candidates not filed

| Candidate | Reason |
|-----------|--------|
| After "Deploy", an "Approval required / Request Rollback" panel appears | Intended design. After a deploy the next available action is "Request Rollback", and the banner previews the approval policy for that action (`src/pages/FeatureCreate.tsx:769-775`, `791-805`, `2054-2062`); its badge says "Request Rollback". The wording could be clearer, but the behaviour is correct. |
| Success toasts linger too long | Not confirmed. The Toaster uses the Sonner default duration of 4 s (`src/layout/AppLayout.tsx:36`). Sonner pauses timers while the tab is hidden, and the automation tab was hidden, so the long display was a recording artifact. |
| Metric create toast quotes differ from the docs | Not a product bug. The toast text is fine; any mismatch is a docs wording issue. |
| Requester sees Environments and Clients links | Intended. Team members can read environments and clients (no GET policy in `logic/policy.rs`). The System Clients and Integrations part is filed as B15. |
