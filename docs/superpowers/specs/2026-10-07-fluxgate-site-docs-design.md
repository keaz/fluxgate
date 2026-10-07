# FluxGate product site and documentation — design

Date: 2026-10-07
Repository: `fluxgate-site` (`keaz/fluxgate-site`), work committed directly on `main`.

## Goal

Turn `fluxgate-site` into the real FluxGate product site:

1. Restyle the site so it looks and feels like the FluxGate admin UI (`feature-toggle-ui`).
2. Rework the home page into a product page.
3. Add documentation that explains every aspect of FluxGate. Each chapter page matches one demo video (`demo-renders/NN-*.mp4`) and its dry-run-tested script (`docs/demo-videos/NN-*.md`), with more detail and concrete examples.
4. Add a developer guide that a developer follows to set up their own FluxGate installation.
5. Add reference pages: configuration, edge server / OpenFeature API, SDKs, and SSO.

### Success criteria

- A visitor who knows the admin UI recognises the site as the same product: same palette, fonts, components, and light/dark behaviour.
- A developer with only Docker can follow the developer guide, copy-pasting from the rendered page, from an empty folder to a first edge evaluation.
- Every demo video has a docs page that tells the same story (Juniper Market, `express-checkout`) and adds concepts, examples, and caveats the video does not have time for.
- No public page exposes private source details (file paths, line numbers, repository internals) or the private `fluxgate` CLI.

## Decisions

| Topic | Decision |
|---|---|
| Video hosting | YouTube. The user uploads the 16 videos and sends the URLs. Until then, each page shows a "Video coming soon" placeholder. |
| Theme | Light by default, dark toggle, follows the OS setting on first visit. Same tokens as the admin UI. |
| Existing pages | Keep `/architecture/`, `/performance/`, `/comparison/`. Restyle them and link them from the product nav. |
| Reference pages | Edge server / OpenFeature API, configuration reference, SDKs, SSO setup. |
| Spring Boot starter | Not published to Maven Central (`1.0.0-SNAPSHOT`, private repo). SDK page leads with OpenFeature SDKs and plain HTTP. The starter is shown with a "Coming soon" badge. |
| Stack | Extend the current React 19 + Vite + pnpm + prerender stack (option A). Astro + Starlight and Docusaurus were rejected because matching the admin UI look is the first requirement and direct reuse of its tokens and components beats theming another framework. |

## Information architecture

### Top navigation

Sticky header with the glass background (`--bg-glass`) used by the admin UI header:
Product · Docs · Architecture · Performance · Comparison · GitHub · theme toggle · "Get started" button (to `/docs/get-started/install/`).

### Product pages

- `/` — home. Hero, proof bar, feature grid by chapter theme, overview video (video 01), screenshot gallery, how it works, OpenFeature and SDK strip, FAQ, call to action into the docs.
- `/architecture/`, `/performance/`, `/comparison/` — current content, new look.

### Documentation

Layout: left sidebar styled like the admin UI sidebar, content column (about 760 px), right table of contents on wide screens, previous/next footer.

URL pattern: `/docs/<chapter>/<slug>/`.

| Group | Pages (slug) | Source |
|---|---|---|
| Overview | `/docs/` landing with chapter cards and a "start here" path | new |
| 1 Get started (`get-started`) | `what-is-fluxgate`, `install`, `teams-users-roles` | videos 01–03 |
| 2 Model your release (`model-your-release`) | `environments-and-pipelines`, `contexts`, `first-feature`, `targeting-rules` | videos 04–07 |
| 3 Connect your app (`connect-your-app`) | `clients-and-edge-server`, `automation-and-ci` | videos 08–09 |
| 4 Ship safely (`ship-safely`) | `approvals-and-policies`, `safety-nets` | videos 10–11 |
| 5 Integrations (`integrations`) | `jira-setup`, `jira-end-to-end`, `jev-ai-assistance`, `sso` | videos 12–14, `feature-toggle/docs/sso.md` |
| 6 Observe and operate (`observe-and-operate`) | `dashboards`, `going-to-production` | videos 15–16 |
| Developer guide | `/docs/developer-guide/` (one page) | demo compose and config files, `fluxgate.wiki/Getting-Started.md` |
| Reference | `/docs/reference/configuration/`, `/docs/reference/edge-api/` (includes OFREP), `/docs/reference/sdks/` | `fluxgate.wiki`, `feature-toggle/docs`, `fluxgate-springboot/README.md` |

About 25 docs pages and 4 product pages.

### Developer guide

One task-oriented runbook:

1. Prerequisites (Docker with Compose; `curl` and `jq` for the checks; Node 20+ only for the sample app).
2. Download `docker-compose.yml` and `config.toml` from the site (`/downloads/docker-compose.yml`, `/downloads/config.toml`, served from `public/downloads/`). They are copies of `docs/demo-videos/assets/docker-compose.demo.yml` and `config.demo.toml`, which live in a different repository. `scripts/sync-downloads.mjs` copies them when run locally from the monorepo checkout; CI does not see the sources, so the copies are committed.
3. Create `.env` with `FLUXGATE_ENCRYPTION_KEY` (with a warning never to change it while the database lives).
4. `docker compose up -d`, then create the first admin.
5. Create a client, add `EDGE_CLIENT_ID` and `EDGE_CLIENT_SECRET` to `.env`, start the edge server (`--profile edge`).
6. Evaluate a flag from `curl` and from a small app.
7. Optional: `TYPESAFE_API_KEY` for Jev AI assistance, Jira, SSO.
8. Production checklist (links to `going-to-production`).

Each step links to the chapter page that explains it. Chapter pages explain concepts. The developer guide is the copy-paste path.

## Chapter page anatomy

### Frontmatter

```yaml
title: Targeting rules
description: Target Canadian Plus users first, then split everyone else 20/80.
chapter: model-your-release
order: 4
video: { number: 7, length: "4:00", captions: true }
takeaway: You can target Canadian Plus users first, then split everyone else 20/80.
prerequisites: [first-feature, contexts]
```

The YouTube ID is not in frontmatter. It lives in `src/content/videos.ts`, keyed by video number, so one file is updated when the URLs arrive.

### Page sections, top to bottom

1. Title, takeaway, video length badge, "builds on" chips from `prerequisites`.
2. Video: click-to-load facade (see YouTube embed below). Placeholder card while the ID is empty.
3. **Before you start**: start state and the roles needed, from the script header table.
4. **Concepts**: what the feature is and why it exists, in more depth than the voiceover.
5. **Step by step**: numbered steps from the scene table. Exact UI labels in bold, routes in code. Optional screenshots.
6. **Examples**: concrete artefacts, for example the stored criteria, a `curl` call to the edge server, an OFREP request and response, an approval policy matrix.
7. **Good to know**: rewritten from the script "Gotchas". Product behaviour is kept, private file paths and line numbers are removed. Real limitations become callouts (for example "criterion priorities start at 0", "clicking another stage discards unsaved criteria").
8. **Troubleshooting**: only where scripts or `docs/product-bugs/` list user-visible problems, written as symptom and fix.
9. Previous/next links and "Next in the series" from the script hand-off line.

### Content rules

- Keep the story bible: Juniper Market, `express-checkout`, `holiday-banner`, `admin` / `priya` / `sam`, the same environments, contexts, and clients.
- Public artefacts only: Docker Hub images `keaz/flux-gate-backend`, `keaz/flux-gate-edge`, `keaz/flux-gate-ui` at `v1.2.0`. No source checkout, no local builds, no `fluxgate` CLI.
- UI labels match v1.2.0 exactly. The demo scripts are the source of truth because they were dry-run tested against those images.
- Open product bugs from `docs/product-bugs/` appear as user-facing caveats without internal detail. Fixed bugs are left out.

### MDX components

`<VideoEmbed>`, `<Steps>`, `<Callout type="note|tip|warn">`, `<TerminalBlock>` (the admin UI's dark terminal style), `<CodeTabs>` (for example curl / JavaScript / Java), `<UiLabel>`, `<RoleBadge>`.

## Visual system

- **Tokens**: copy the `:root` and `.dark` token blocks from `feature-toggle-ui/src/index.css` into `src/styles/tokens.css`, with the same Tailwind v4 `@theme` mapping. Drop the legacy aliases.
  - Light: background `#f7f9fc`, card `#ffffff`, primary `#009966`, small primary text `#006644`.
  - Dark: background `#060b18`, card `#0f1629`, primary `#00e599`.
- **Fonts**: DM Sans (body) and JetBrains Mono (code), self-hosted as woff2.
- **Theme**: `ThemeProvider` adapted from the admin UI. An inline script in `index.html` reads the stored choice (inside try/catch), falls back to `prefers-color-scheme`, and sets `.dark` before first paint.
- **Components copied from the admin UI** (`src/components/ui/`): `button`, `card`, `badge`, `tabs`, `eyebrow`, `kbd`, `terminal-block`, `page-header`, and the `cn()` helper. Radix only for Tabs and Dialog (mobile nav, search).
- **Product pages**: flat surfaces that alternate `--background` and `--bg-alt` bands, `--elev-card` shadows, a soft `--accent-glow` behind the hero screenshot. No heavy gradients.
- **Screenshots**: retake the key screens from a local v1.2.0 demo stack in both themes (features list, stage editor, approvals, dashboards). The hero swaps the screenshot with the theme. Benchmark charts stay as they are.
- **Docs shell**: sidebar items use the admin UI styles (`h-9` rows, `bg-accent-dim` for the active item, chapter group headers like nav groups). Code blocks use the dark terminal style in both themes.
- **Accessibility**: WCAG AA contrast, visible focus rings (`--ring`), skip link, `prefers-reduced-motion` respected, 16 px side gutter and no horizontal scroll on phones.

## Technical architecture

The current pattern stays: `App` renders by `path`, `entry-server.tsx` renders each route to a string, `scripts/prerender.mjs` writes `dist/<route>/index.html` and the sitemap, and links are plain `<a>` with full page loads.

1. **Route registry** (`src/routes.ts`) replaces the hardcoded list in `site.ts`.
   - Product routes are declared by hand with their current meta and JSON-LD.
   - Docs routes come from `import.meta.glob('./content/docs/**/*.mdx')`. The path comes from the file location. Meta comes from frontmatter (`remark-frontmatter` + `remark-mdx-frontmatter`).
   - The build fails on a duplicate slug, a missing `title` or `description`, an unknown `chapter`, or a `prerequisites` entry that does not resolve.
2. **Code splitting**: the server build imports all pages. The client loads only the module for the current route, then calls `hydrateRoot`.
3. **MDX pipeline**: `@mdx-js/rollup`, `remark-gfm`, `rehype-slug`, `rehype-autolink-headings`, and `@shikijs/rehype` with a light and a dark theme switched by `.dark`. The table of contents (h2, h3) is extracted at build time.
4. **Search**: Pagefind runs after prerender (`pagefind --site dist`) and indexes docs content only (`data-pagefind-body`). A search dialog opens on `⌘K` or `/`, like the admin UI command palette. The index loads on first open.
5. **SEO**: `TechArticle` and `BreadcrumbList` JSON-LD per docs page, `VideoObject` JSON-LD when a YouTube ID exists. The sitemap is generated from the registry.
6. **YouTube embed**: `src/content/videos.ts` maps video number to YouTube ID. The facade shows the thumbnail from `i.ytimg.com` and a play button. The `youtube-nocookie.com` iframe loads only after a click. Captions are on YouTube.
7. **Infrastructure**: no Terraform change. S3 serves `docs/.../index.html` like the current routes. The plan verifies that S3 and Cloudflare serve Pagefind's `*.pf_*` files with working content types.
8. **Dependencies added**: `tailwindcss` v4, `@tailwindcss/vite`, `@radix-ui/react-tabs`, `@radix-ui/react-dialog`, `class-variance-authority`, `clsx`, `tailwind-merge`, MDX, Shiki, and Pagefind packages, Vitest. Package manager stays pnpm.

## Testing and verification

### Automated

- **Registry tests** (Vitest): unique slugs, required frontmatter, each chapter's pages in order, prerequisites resolve.
- **Content lint** (`scripts/check-docs.mjs`, part of `pnpm build`). It fails on:
  - private source references (for example `\.(rs|tsx?):\d+`, `src/`, `feature-toggle-backend`, `feature-toggle-ui`);
  - `fluxgate` CLI commands;
  - image references other than `keaz/flux-gate-*:v1.2.0` or `:latest`;
  - internal links to routes that are not in the registry.
- **Component tests**: `VideoEmbed` shows the placeholder for an empty ID and renders no iframe before a click; the theme script sets `.dark` from storage or the OS setting; table of contents extraction.
- **Build smoke test**: every registry route exists in `dist/` with the right `<title>`, canonical link, and JSON-LD.

### Manual, before any completion claim

- Every page in light and dark at 1440 px and 375 px: no horizontal scroll, sidebar turns into a drawer on mobile.
- Search returns the expected pages for "targeting", "OFREP", and "encryption key".
- Developer guide run end to end in an empty folder with the public images, copy-pasting every command from the rendered page, up to the first edge evaluation.
- Lighthouse on `/` and one docs page: target 95 or more for performance, accessibility, and SEO.

## Delivery phases

Each phase leaves the site buildable and deployable.

1. **Foundation**: Tailwind v4, tokens, theme, copied UI components, new header and footer. The four existing pages restyled.
2. **Docs engine**: MDX pipeline, route registry, sidebar, table of contents, previous/next, MDX components, prerender extension, search, content lint.
3. **Content: Get started and developer guide.**
4. **Content: chapters 2 to 6.**
5. **Reference pages**: configuration, edge API and OFREP, SDKs, SSO.
6. **Product home rewrite and screenshot retakes** in both themes.
7. **YouTube IDs** (after the user sends the URLs) and final verification.

## Out of scope

Documentation versioning, translations, blog, analytics, a CMS, and changes to the FluxGate product. Product bugs found while writing the docs are logged in `docs/product-bugs/`, not fixed in this project.
