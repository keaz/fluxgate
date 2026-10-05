# 06 · Create your first feature

| Field | Value |
|---|---|
| Website section | Model your release › Features |
| Length target | 4:00 |
| Takeaway | You create `express-checkout` with an owner, a ticket, two variants and the `checkout-release` pipeline, and read the feature list and detail page. |
| Start state | End of 05: contexts exist. |
| End state | Feature `express-checkout` (CONTEXTUAL, kind Release, variants `classic` and `express`, pipeline `checkout-release`, no criteria); feature `holiday-banner` (SIMPLE). |
| Prerequisites | Signed in as `priya`; team `Checkout` selected in "Select team". |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Contexts list at `/contexts` with `country` and `user_tier`. | A flag with no owner, no ticket and no end date is how a codebase ends up with a hundred flags nobody dares delete. So when you create express-checkout, you record who owns it, why it exists and when it should be gone, right from the start. | |
| 0:25 | Click "Features" under "Build" to open `/features`, click "Create New Feature". | Open Features and click create new feature. | Highlight "Create New Feature" |
| 0:32 | On `/features/create` titled "Create Feature", the "Basic Information" card: fill "Name" `express-checkout`, "Description" `One-tap checkout`, "Purpose" `Cut checkout steps for returning shoppers`, "Ticket / Reference URL" `https://juniper.atlassian.net/browse/CHK-142`. | Under basic information, the name is the key your code asks for, so keep it stable. Add a description, which shows in the list, and a purpose, which is the why. Then paste the ticket link, here the Jira issue CHK-142, so anyone who finds the flag can trace it back. | Zoom on "Ticket / Reference URL" |
| 0:58 | Set "Feature Type" to `CONTEXTUAL`, "Kind" to "Release". | Feature type decides what the flag can do. Contextual flags carry variants and targeting rules. Simple flags are plain on or off. Kind records what the flag is for. A release flag is meant to be removed once the rollout ends. | Highlight "Kind" |
| 1:20 | Set "Lifecycle" to `ACTIVE`, "Owner" to `priya`, "Expiry" to a date at the end of Q4, "Tags" to `checkout, q4`. | Set the lifecycle to active, the owner to priya, and an expiry at the end of the quarter. The expiry feeds the feature list, so flags that outlive their rollout are easy to find. Owner is free text, so a person or a team both work. Tags are comma separated. | Zoom on "Expiry" |
| 1:46 | The "Feature Variants" card has appeared. Click "Add Variant" twice. In the rows set "Variant Key" `classic` and `express`, "Type" String, "Value" `classic` and `express`. | Because the type is contextual, a variants card appears. A variant is a named value the flag can return. Add two: classic, the checkout you have today, and express, the new one. Both are strings. | Highlight the "Variant Key" column |
| 2:05 | Open "Pipeline Template", the selector reads "Select a Pipeline"; choose `checkout-release`. The stage graph appears with Development, Staging and Production. | Now pick the pipeline template. Choose checkout-release, and the graph fills in with your three environments in order. This feature gets one stage for each. | Zoom on the stage graph |
| 2:21 | Click "Create Feature". The page becomes "Edit Feature" at `/features/:id/edit`; scroll to "Blast Radius". | Save it. FluxGate drops you into the editor, where the blast radius panel summarises what a change to this flag could reach: environments, clients, contexts and dependencies. It's empty today, and it fills in as you connect apps. | Highlight "Blast Radius" |
| 2:41 | Click "Back to Features". The list at `/features` shows `express-checkout` with its badges. | Back in the list, filters sit above the table: name, type, status, lifecycle, owner, tag and more. The active badge means the flag is switched on, yet nothing is served until a stage deploys. The flag also shows its type, its lifecycle and its kind. | Highlight the status badge first, then the other badges |
| 3:04 | Point at "Saved Views"; click the row's "View Details" button, which opens `/features/:id`. | Saved views keep a set of filters in your browser, which helps once the list grows. View details opens the read-only page: overview, stages, variants, dependencies and activity. | Highlight the tab row |
| 3:20 | Back to `/features`, click "Create New Feature". Create `holiday-banner` with "Feature Type" `SIMPLE` and "Pipeline Template" `checkout-release`, leave "Kind" on "Not set", click "Create Feature". Speed up the footage. | One more flag. Holiday-banner is simple: on or off, no variants. A later video uses it for the kill switch and scheduled changes, so give it the same pipeline. Leave its kind unset for now. | Time-lapse; caption: `holiday-banner`, SIMPLE |
| 3:39 | Features list with both flags. | Two flags, still without rules. So far this has been bookkeeping. The next video is where the flag starts making decisions. | |

## Hand-off

Next: add targeting rules to `express-checkout` on the Development and Staging stages (video 07).

## Gotchas while recording

- Account: `priya`. Creating a feature has no role check, and `priya` is a member of `Checkout`. Only editing a feature (`PATCH /features/{id}`) needs an admin or `Team Admin` (`feature-toggle-backend/src/logic/policy.rs:394-398`); this video does not edit anything. The "Update Feature" button on the edit page therefore fails for `priya`; do not click it.
- Deviation from the brief: the "Blast Radius" panel is rendered only in edit mode (`feature-toggle-ui/src/pages/FeatureCreate.tsx:1920`, inside `{isEdit && (`), so it does not appear on the create page. After "Create Feature" the app navigates to `/features/:id/edit` (`FeatureCreate.tsx:1426`), so the script shows it there. Its sub-labels are "Environments", "Clients", "Contexts", "Dependencies" and "7d evals" (`FeatureCreate.tsx:1944-1960`).
- Field order and labels on the create page (`FeatureCreate.tsx:1589-1823`): "Name", "Description", "Purpose", "Ticket / Reference URL", then "Feature Type", "Kind", "Dependencies", "Lifecycle", "Owner", "Expiry", "Cleanup Reason", "Tags". Feature type options are `CONTEXTUAL` and `SIMPLE` (`FeatureCreate.tsx:91-93`); lifecycle options are `DRAFT`, `ACTIVE`, `DEPRECATED`, `ARCHIVED`, with `DRAFT` as the default (`FeatureCreate.tsx:95`, state default at `:430`). The script picks `ACTIVE`.
- "Kind" option label for `release` is "Release"; the `ops` option reads "Ops / kill switch" (`src/lib/flagKind.ts:5-18`). The select shows "Not set" until a value is chosen (`components/features/FlagKindField.tsx:39`). Leave `holiday-banner` on "Not set": video 14 classifies flags and expects an unclassified one. AI kind suggestions appear only when `TYPESAFE_API_KEY` is set; if a suggestion chip shows up, ignore it for `express-checkout` or choose "Release" explicitly.
- "Feature Variants" appears only after "Feature Type" is `CONTEXTUAL` (`FeatureCreate.tsx:1864-1872`). "Add Variant" creates a row with the key `variant-1`, type String and an empty value (`components/features/VariantManager.tsx:18-25`); rename the key. Column headers: "Variant Key", "Type", "Value", "Description" (`VariantManager.tsx:173-182`). A `SIMPLE` flag shows "Simple features are basic on/off flags" instead.
- "Pipeline Template" shows only on the create page (`FeatureCreate.tsx:1879-1886`); placeholder "Select a Pipeline". Choosing a pipeline shows the toast "Pipeline template loaded". The "Rollout Templates" card below it is not used in this video; it comes back in video 07.
- "Expiry" is a `datetime-local` field: use a date at the end of the quarter in the recording environment's timezone.
- Deviation from the brief: the brief says the list shows "badges, Saved Views". Saved views are stored in the browser's local storage per team (`components/features/FeatureTable.tsx:180,655`, key `fluxgate:feature-views:<team id>`), not on the server, so the voiceover says "in your browser". "Save View" and "Delete" sit next to the "View Name" field; the script only points at them. "View Details" is an icon button with that title (`FeatureTable.tsx:804`); clicking the feature name button does the same.
- The detail page tabs are "Overview", "Stages", "Variants", "Dependencies" and "Activity" (`pages/FeatureDetail.tsx:480-484`). Its header shows the badge "Enabled" rather than "ACTIVE".
- Do not claim a flag is "live" at this point: every stage is still `NOT_DEPLOYED`.
