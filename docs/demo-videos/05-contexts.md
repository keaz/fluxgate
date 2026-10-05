# 05 · Contexts

| Field | Value |
|---|---|
| Website section | Model your release › Contexts |
| Length target | 2:30 |
| Takeaway | You declare the facts a rule can use, `country` and `user_tier`, and see how your app sends them at evaluation time. |
| Start state | End of 04: environments and pipeline exist. |
| End state | Contexts `country` (US, CA, UK) and `user_tier` (free, plus). |
| Prerequisites | Signed in as `priya`; team `Checkout` selected in "Select team". |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | Pipelines list at `/pipelines` showing `checkout-release`. | The rule you want to write is Canadian Plus users first. But FluxGate can't know a user's country or plan. Your app has to tell it, on every evaluation. Contexts are where you declare which of those facts exist, so the rule editor can offer them instead of you retyping them. | |
| 0:25 | Click "Contexts" under "Build" to open `/contexts`; the page reads "Define context variables for targeting rules". Click "Create New Context". | Open Contexts. The page is for defining context variables for targeting rules. Click create new context. | Highlight "Create New Context" |
| 0:34 | On `/contexts/create` titled "Create Context": type `country` in "Context Key". | A context is a key with a list of known values. The first key is country. Use the same spelling your app will send. | |
| 0:47 | Under "Context Values" type `US` in the empty field, click "Add Value", type `CA`, click "Add Value", type `UK`. | Add the values: US, then add value for CA, and once more for UK. These are the values your app is expected to send. | Zoom on the three value fields |
| 1:00 | Click "Save Context". The list at `/contexts` shows `country`. | Save it, and country appears in the list. | |
| 1:06 | Repeat for `user_tier` with values `free` and `plus`. Speed up the footage. | Do the same for user underscore tier, with free and plus. | Time-lapse; caption: `user_tier` |
| 1:14 | The "Key" column lists `country` and `user_tier`. | Two contexts, which is all the targeting in this series needs. You can add more later when a rule needs a new fact, such as app version or device type. | |
| 1:29 | Cut to a code editor showing the JSON from the Callout snippet section at the end of this script. | Here's the other half. When your app asks for a flag, it sends a context object with those keys: the user's country, the plan, and one more thing, a bucketing key. The rule editor will match its conditions against these keys. Video 8 sends this for real. | Show the JSON from the Callout snippet section below |
| 1:52 | Point at `bucketingKey` in the snippet. | The bucketing key is a stable id for the user. For a percentage split, FluxGate hashes it together with the flag key to pick a bucket. The same user id lands in the same bucket every time, so nobody flips between checkout versions on refresh. Use something stable, like a user id, not a session or a random number. | Highlight `bucketingKey` |
| 2:20 | Back on `/contexts`. | Contexts done. Now the flag itself. | |

## Hand-off

Next: create the `express-checkout` flag, its variants and its pipeline, plus the `holiday-banner` flag (video 06).

## Gotchas while recording

- Account: `priya`, same gate reasoning as video 04. Creating a context has no role check; only editing (`PATCH /contexts/{id}`) needs an admin or `Team Admin` (`feature-toggle-backend/src/logic/policy.rs:379-383`). Start from the end of video 04, where `priya` is already signed in.
- Create form labels (`pages/ContextCreate.tsx:144,159,163`): "Context Key", "Context Values", "Add Value". The submit button reads "Save Context" (`ContextCreate.tsx:226`), and the page title is "Create Context". The form starts with one empty value field, so type the first value before clicking "Add Value". The value fields have no labels, only the placeholder "e.g., admin, US, mobile"; a remove button appears on hover.
- Deviation from the brief: the context list has a single "Key" column and does not show the values (`components/tables/ContextTable.tsx:59-65`). Open the edit page only if you want to show the values again; do not save any change there.
- A context key is free text in the rule editor. Defining a context does not restrict which keys a rule can use. It feeds the key suggestions, and the "In List" operator can use a whole context as its list (`components/CompoundRuleBuilder.tsx:368-376,418-436`). The voiceover claims only that.
- The bucketing detail is from `feature-toggle/evaluation-engine/src/lib.rs:490-535`: the bucket is `SHA256("<flag key>:<targeting key>")`, and a weighted split cannot place a user who sends no key. The edge API wiki lists `context.bucketingKey` as required (`fluxgate.wiki/Edge-Server-API.md:46`). The snippet below omits the environment id on purpose; video 08 adds it.
- The voiceover spells `user_tier` as "user underscore tier" so a text-to-speech voice reads it correctly.

## Callout snippet

Show this as a code card at 1:29. It is not a UI label, so it lives here instead of in the scene table.

```json
{
  "bucketingKey": "user-42",
  "country": "CA",
  "user_tier": "plus"
}
```
