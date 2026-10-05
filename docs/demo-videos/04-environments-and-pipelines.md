# 04 · Environments and pipelines

| Field | Value |
|---|---|
| Website section | Model your release › Environments and pipelines |
| Length target | 3:00 |
| Takeaway | You model Development, Staging and Production as environments, then chain them into the `checkout-release` pipeline that every feature starts from. |
| Start state | End of 03: team and users exist. |
| End state | Environments Development, Staging, Production; pipeline `checkout-release` (Dev → Staging → Production). |
| Prerequisites | Signed in as `priya`; team `Checkout` selected in "Select team". |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | System Overview at `/dashboard/overview`, signed in as `priya`, team `Checkout` selected. | You have one flag, but your code runs in more than one place: a laptop, a staging cluster, production. If FluxGate treats those as the same place, a change you meant to test can reach customers. So you model each place as an environment, then chain the environments into a pipeline. That's this video: three environments, then the pipeline that links them. | |
| 0:30 | Click "Environments" under "Build" to open `/environments`, click "Create New Environment". | Open Build, then Environments. An environment is a deployment target that a flag can be switched on or off in. Click create new environment. | Highlight "Create New Environment" |
| 0:43 | In the dialog fill "Environment Name" `Development`, leave "Environment Type" on `Development`, leave "Enabled" on, click "Create Environment". | Name the first one Development. The type is more than a label: an approval policy can later apply to production only, and it finds production by this type. Leave it enabled and create it. | Zoom on "Environment Type" |
| 1:00 | Repeat for `Staging` (type `Staging`) and `Production` (type `Production`). Speed up the footage. | Do the same for Staging and Production. Pick the matching type for each one, since the type is what policies read. | Time-lapse; caption: `Staging`, `Production` |
| 1:12 | The "Environments" table lists all three with their types. | Three environments, each with its own type and status. The names are yours to choose. The type is the part FluxGate reads. | Highlight the "Type" column |
| 1:25 | Click "Pipelines" under "Build" to open `/pipelines`, click "Create New Pipeline". | Environments alone don't say what order a change travels through them. That's the pipeline. Open Pipelines and click create new pipeline. | |
| 1:37 | On `/pipelines/create` titled "Create Pipeline": type `checkout-release` in "Pipeline Name". | Call it checkout-release. | |
| 1:41 | Under "Pipeline Stages", open the "Environment" selector on the first stage and pick `Development`. | Under pipeline stages, the first node is the start of the path. Pick Development for it. Every stage is tied to exactly one environment. | Zoom on the stage node |
| 1:55 | Click the small plus button under the first stage, pick `Staging` in the new stage. Click the plus under that stage, pick `Production`. | The small plus button under a stage adds the next stage, connected to it. Add Staging after Development, then Production after Staging. | Highlight the plus button |
| 2:07 | Click "Create Pipeline". The list at `/pipelines` shows `checkout-release`. | Create the pipeline, and it shows up in the list. You can reuse it for as many flags as you like. | |
| 2:19 | Zoom on the pipeline name in the list. | Why bother? A pipeline is the template a feature starts from. When you create a feature next, you choose this pipeline and the feature gets one stage per environment, in this order. Each stage is then requested, approved and deployed on its own, so Development can go live today while Production waits. | |
| 2:44 | Back on `/pipelines`. | Next, contexts: the facts your targeting rules will match on, such as a user's country or plan. | |

## Hand-off

Next: define the `country` and `user_tier` contexts that targeting rules will use (video 05).

## Gotchas while recording

- Account: the script uses `priya`, not `admin`. Creating an environment, pipeline, context or feature has no role check. The backend route policy only guards edits: `PATCH` on environments, pipelines, contexts and features needs a system admin or `Team Admin` (`feature-toggle-backend/src/logic/policy.rs:379-399`), and no `POST` route appears in that table. The sidebar items under "Build" have no gate (`feature-toggle-ui/src/layout/navConfig.ts:75-81`). Sign in as `admin` instead if you also want to edit or delete a row on camera.
- Video 03 ends with `priya` signed in, so no account switch is needed here. If the team selector looks stale after switching users, reload the page.
- Deviation from the brief: the dialog title and its submit button are both "Create Environment" (`modals/CreateEnvironmentModal.tsx:90,157`); "Create New Environment" is the button on the page (`pages/EnvironmentsPage.tsx:48`). The type choices are `Development`, `Staging` and `Production` (`CreateEnvironmentModal.tsx:122-124`). Environment names must be unique within a team (`feature-toggle-backend/src/rest/environment.rs:77`).
- Pipeline editor: there is no "Add Stage" button. A stage is added with a small unlabelled plus icon below a node (`components/PipelineNode.tsx:37-44`). The first node is labelled "Input Node" in code, but the node component never renders that label (`PipelineNode.tsx:15-45`). The environment selector's placeholder reads "Environment" (`PipelineNode.tsx:24`). The page labels are "Pipeline Name" and "Pipeline Stages" (`pages/PipelineCreate.tsx:256,271`). The submit button reads "Create Pipeline" and shows the toast "Pipeline created successfully" (`PipelineCreate.tsx:203,301`).
- Deviation from the brief: the brief says the pipeline gives "enforced promotion order". The code does not enforce that at deploy time. Nothing in the stage-change path checks that the parent stage is deployed first (`feature-toggle-backend/src/logic/feature.rs:1816-2000`, `src/validation.rs:51-81`). The pipeline fixes which environments a feature has and the order of its stages, so the voiceover claims only that.
- The pipeline list shows only "Name" and "Description" columns (`components/tables/PipelineTable.tsx:79,84`), not the stages. The environment list columns are "Environment ID", "Name", "Type" and "Status" (`components/tables/EnvironmentTable.tsx:95-111`).
- Pipelines and environments are created for the team chosen in the header selector; with no team selected both forms show "Please select a team first." (`CreateEnvironmentModal.tsx:52-56`).
