# 03 · Teams, users and roles

| Field | Value |
|---|---|
| Website section | Get started › Teams and users |
| Length target | 3:30 |
| Takeaway | You create a team, add a requester and an approver, and learn what the three system roles allow. |
| Start state | End of 02: `admin` signed in, no team. |
| End state | Team `Checkout`; users `priya` (Requester) and `sam` (Approver) in `Checkout`; `priya` has set a permanent password. |
| Prerequisites | Signed in as `admin`. |

## Scenes

| Time | On screen | Voiceover | Callout |
|---|---|---|---|
| 0:00 | System Overview at `/dashboard/overview`, signed in as `admin`. | Approvals only mean something when the person who asks and the person who approves are different people. FluxGate enforces that: a requester cannot approve their own request. So before modeling anything, set up a team and two users, one to request changes and one to approve them. |  |
| 0:21 | Expand "Settings", click "Teams" to open `/settings/teams`, click "Create New Team". | Open Settings, then Teams. A team is the group that owns features and pipelines. Click create new team. | Highlight "Create New Team" |
| 0:31 | In the dialog fill "Team Name" `Checkout` and "Description" `Juniper Market checkout squad`, click "Create Team". | Name it Checkout and give it a short description. Once saved, the team appears in the selector at the top of the page, which scopes what you see to that team. | Zoom on the "Select team" selector in the header |
| 0:47 | Click "Users" to open `/settings/users`, click "Create New User" to reach `/users/create`. | Now the users. Open Users and click create new user. |  |
| 0:53 | On "Create User": fill "Username" `priya`, "Password" `<redacted>`, "First Name", "Last Name", "Email", click "Create User". | The first user is priya, a Checkout developer. Fill in a username, a password, a name and an email, then click create user. The username and password are the only required fields. | Blur the password field |
| 1:11 | The edit page opens on the "Assign Teams" tab: under "Team Assignment" tick `Checkout`, click "Assign Selected Teams". | FluxGate drops you into the assignment tabs. Under team assignment, tick Checkout and assign the selected teams. |  |
| 1:21 | Switch to the "Assign Roles" tab: under "Role Assignment" tick `Requester`, click "Assign Selected Roles". | Under role assignment, tick Requester. Priya can ask for changes to be deployed, but cannot approve them. Select the role, then click assign selected roles. |  |
| 1:35 | Switch to the "Credentials" tab: fill "Temporary Password" and "Confirm Temporary Password" with `<redacted>`, click "Set Temporary Password". | On the credentials tab, set a temporary password. Priya has to replace it on first sign in, so nobody else ever needs to know the final password. A toast confirms it. | Blur both password fields |
| 1:51 | Back to `/users/create`: repeat for `sam` with team `Checkout`, role `Approver`, and a temporary password. Speed up the footage. | Repeat for sam, the release manager. Same team, same steps, but this time give sam the Approver role. Now the Checkout team has one person who asks and one who approves. | Time-lapse; caption: `sam`, Approver |
| 2:07 | Click "Roles" to open `/settings/roles`; "Global Roles" lists "Existing roles". | What do the roles mean? Open Roles. Approver can approve deployment requests and stage changes. Requester can request them. Team Admin can manage team settings and members. They apply across every team, and the three system roles are protected. | Highlight each role description in turn |
| 2:25 | Click "Single Sign-On" to open `/settings/sso`, then "Notifications" to open `/settings/notifications`. | Two more pages, only as a pointer. Single sign-on lets people sign in with an OpenID Connect provider and maps identity provider groups to roles and teams; video 16 sets it up. Notifications is where you configure email and SMS gateways. | Lower third: SSO, video 16 |
| 2:44 | Avatar menu, click "Log out"; at `/login` fill `priya` and the temporary password, click "Sign in". | Now sign out and sign in as priya with the temporary password. | Blur the password field |
| 2:52 | FluxGate redirects to `/temporary-password-reset` titled "Update Your Password": fill "Current Password", "New Password", "Confirm New Password", click "Update Password". | FluxGate stops here and asks for a new password before anything else. Enter the temporary one, choose a permanent password, and update it. | Blur all three fields |
| 3:06 | Open the avatar menu and show "Reset password", which opens `/reset-password`. | Later, anyone can change their own password from the avatar menu, under reset password. Priya is now ready for the next video. |  |

## Hand-off

Next: create the Development, Staging and Production environments and the `checkout-release` pipeline (video 04).

## Gotchas while recording

- Deviation from the brief: the brief puts the SSO and notifications mention after the `priya` sign-in. Both pages are admin-only (`navConfig.ts`, `gate: 'admin'`), so `priya` cannot reach them. The script shows them as `admin` before signing out.
- Create flow in the code (`feature-toggle-ui/src/pages/UserEdit.tsx`): create mode shows only the "Basic Details" tab with required "Username" and "Password" and the "Create User" button. After creation the page opens the edit URL with the "Assign Teams", "Assign Roles" and "Credentials" tabs. The brief's "Team Assignment" and "Role Assignment" are headings inside those tabs (`UserEdit.tsx:603`, `:659`); the tab names are "Assign Teams" and "Assign Roles" (`UserEdit.tsx:81-82`).
- The "Credentials" tab is visible to admins and users with team management access (`UserEdit.tsx:59`). "Set Temporary Password" is both a heading and the button label; the button is enabled only after both fields are filled, and the password must be at least 8 characters.
- The create user form requires a "Password" even though a temporary password is set afterwards. Type any placeholder and replace it in the "Credentials" tab; all password fields are `<redacted>`.
- Team dialog: title and submit are both "Create Team"; labels "Team Name" and "Description" (`components/modals/CreateTeamModal.tsx`). The header selector is labelled "Select team" (`layout/Header.tsx:77`).
- Role descriptions come from the migration the backend migration `20250903000000_create_roles.sql:22-24`: Approver "Can approve deployment requests and stage changes", Requester "Can request deployment and stage changes", Team Admin "Can manage team settings and members". The "Roles" page text is "Global Roles", with a card titled "Existing roles" (`pages/RolesPage.tsx:97,159`). The voiceover paraphrases the descriptions.
- The rule that requesters cannot approve their own request is the error `Requesters cannot approve their own request` in `feature-toggle-backend/src/lib.rs:42`. Do not stage a self-approval attempt in this video.
- The overview title is "System Overview"; the avatar menu items are "Reset password" and "Log out" (`layout/Header.tsx:137-146`). The temporary password page title is "Update Your Password" and the button is "Update Password" (`pages/TemporaryPasswordReset.tsx`).
- End state: leave `priya` signed in. Video 04 may need `admin` for environments; sign in as `admin` there if the pages are not visible to a requester.
