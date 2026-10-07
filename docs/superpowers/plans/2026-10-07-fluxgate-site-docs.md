# FluxGate Product Site and Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle `fluxgate-site` to the FluxGate admin UI design system, turn it into a product site, and add about 25 documentation pages (one per demo video, a developer guide, and reference pages) with search.

**Architecture:** Keep the existing React 19 + Vite + pnpm + static prerender stack. Add Tailwind v4 with the admin UI's tokens and copied shadcn primitives. Docs are MDX files under `src/content/docs/`; a typed registry built from their frontmatter drives routes, sidebar, sitemap, and JSON-LD. The server build renders every route to HTML; the client lazy-loads only the current page's MDX chunk before hydrating. Pagefind indexes the prerendered docs for static search.

**Tech Stack:** React 19, TypeScript ~6, Vite 8, Tailwind CSS 4.3, Radix (Dialog, Tabs, Slot), class-variance-authority, MDX 3 (`@mdx-js/rollup`), Shiki 4 (`@shikijs/rehype`), Pagefind 1.5, Vitest 5 + Testing Library + jsdom, pnpm.

**Spec:** `docs/superpowers/specs/2026-10-07-fluxgate-site-docs-design.md` (in the monorepo root `/Users/kasunranasinghe/Projects/FeatureToggle`). Read it before starting.

## Where things are

- Site repository (all code changes, all commits): `/Users/kasunranasinghe/Projects/FeatureToggle/fluxgate-site` (git remote `keaz/fluxgate-site`). Every path in this plan is relative to this folder unless it starts with `../`.
- Monorepo sources the docs are written from (read-only for this plan):
  - Demo scripts: `../docs/demo-videos/NN-*.md` and `../docs/demo-videos/README.md` (story bible, recording setup).
  - Demo stack files: `../docs/demo-videos/assets/docker-compose.demo.yml`, `../docs/demo-videos/assets/config.demo.toml`.
  - Product bugs found while recording: `../docs/product-bugs/2026-10-demo-recording.md`.
  - Older wiki: `../fluxgate.wiki/*.md` (may be stale; the demo scripts win on any conflict).
  - Current edge API doc: `../feature-toggle/docs/edge-server-api.md`. SSO doc: `../feature-toggle/docs/sso.md`.
  - Spring Boot starter README: `../fluxgate-springboot/README.md`.
  - Admin UI design system: `../feature-toggle-ui/src/index.css`, `../feature-toggle-ui/src/components/ui/*`.

## Global Constraints

- Package manager: `pnpm` only. Node 22 (CI uses `node-version: 22`, pnpm `10.28.2`).
- Commit directly on `main` of the `fluxgate-site` repository. Every commit message ends with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Site URL: `https://flux.forgeopslabs.com`. Docs URL pattern: `/docs/<chapter>/<slug>/` with a trailing slash.
- Public artifacts only in docs: Docker Hub images `keaz/flux-gate-backend`, `keaz/flux-gate-edge`, `keaz/flux-gate-ui` at tag `v1.2.0` (or `latest`). No source checkout, no local image builds, no `fluxgate` CLI.
- No private source references on any public page: no file paths with line numbers, no `feature-toggle-backend`, `feature-toggle-ui`, `evaluation-engine`, `feature-edge-server`, `fluxgate.wiki`.
- Downloadable files keep the video names: `/downloads/docker-compose.demo.yml` and `/downloads/config.demo.toml`.
- Story bible stays: Juniper Market, team `Checkout`, features `express-checkout` (variants `classic`, `express`) and `holiday-banner`, users `admin` / `priya` (Requester) / `sam` (Approver), environments Development / Staging / Production, pipeline `checkout-release`, contexts `country` (US, CA, UK) and `user_tier` (free, plus), clients `juniper-web` and `checkout-service`, Jira project `CHK`, ticket `CHK-142`.
- UI labels in docs match v1.2.0 exactly as written in the demo scripts.
- Theme: light by default, `.dark` class on `<html>`, OS preference on first visit, stored choice under the `localStorage` key `fluxgate-site-theme`. Every storage access is wrapped in `try/catch`.
- Design tokens are copied verbatim from `../feature-toggle-ui/src/index.css` (values listed in Task 1).
- YouTube embeds use `https://www.youtube-nocookie.com/embed/<id>`; no iframe exists before the visitor clicks play.
- Layout works at 375 px wide with a 16 px side gutter and no horizontal page scroll.
- Code blocks use the dark terminal style in both site themes (single Shiki theme `github-dark-default`).

## Review Focus

1. A docs page opened directly from its URL (prerendered HTML, before JavaScript runs) must contain the full article text, not an empty shell. Pinned by `scripts/check-dist.mjs` in Task 7.
2. Theme-dependent markup (toggle icon, themed screenshots) must be identical on server and client, or React hydration fails on every dark-mode visit. Pinned by the `renderToString` equality test in Task 2.
3. `localStorage` that throws (private mode, blocked site data) must not break the theme script or the toggle. Pinned by tests in Task 2.
4. Duplicate headings and headings with inline code must produce table-of-contents links that match the heading ids that `rehype-slug` writes. Pinned by the plugin test in Task 5.
5. A path typed without the trailing slash (`/docs/get-started/install`) or with `index.html` must resolve to the same page; search opened when the Pagefind index is missing (dev server) or with no results must show a message, not crash. Pinned by the `findRoute` tests in Task 7 and the search tests in Task 10.

---

## File structure (end state)

```
fluxgate-site/
  index.html                         theme pre-paint script, theme-color metas, no Google Fonts
  vite.config.ts                     react, tailwind, mdx (+ remark/rehype plugins), @ alias
  vitest.config.ts                   jsdom test config merged with vite config
  mdx/remark-export-toc.ts           remark plugin: export const toc = [...] from h2/h3
  mdx/remark-export-toc.test.ts
  docs/AUTHORING.md                  how to write a docs page (template + rules)
  public/downloads/                  docker-compose.demo.yml, config.demo.toml (synced copies)
  public/images/ui/                  retaken UI screenshots, <name>-light.jpg / <name>-dark.jpg
  scripts/prerender.mjs              async render, registry routes, sitemap
  scripts/check-docs.mjs             content lint (runs first in build)
  scripts/check-dist.mjs             built-output smoke test (runs last in build)
  scripts/sync-downloads.mjs         copies demo files from the monorepo
  scripts/lib/doc-paths.mjs          file -> URL mapping for node scripts
  scripts/lib/lint-docs.mjs          pure lint rules
  scripts/lib/*.test.mjs
  src/main.tsx                       loads current doc chunk, then hydrates
  src/entry-server.tsx               async render(path)
  src/App.tsx                        shell + route switch
  src/index.css                      tailwind, fonts, tokens, prose
  src/styles/tokens.css              admin UI tokens + @theme mapping
  src/styles/doc-prose.css           typography for MDX articles
  src/lib/utils.ts                   cn()
  src/lib/paths.ts                   normalizePath()
  src/theme/theme.ts                 resolveTheme, read/write/apply
  src/site.ts                        constants, product meta, doc meta, getRouteMeta
  src/routes.ts                      Route union, routes, findRoute
  src/content/chapters.ts            CHAPTERS
  src/content/schema.ts              DocFrontmatter, parseFrontmatter
  src/content/registry.ts            pathFromFile, buildDocRegistry, getDocNav, getPrevNext
  src/content/docs-index.ts          import.meta.glob wiring: docEntries, docLoaders
  src/content/doc-module.ts          DocModule, TocEntry types
  src/content/videos.ts              video number -> YouTube id
  src/content/docs/**.mdx            the docs
  src/components/ui/*.tsx            copied admin UI primitives
  src/components/ThemeToggle.tsx
  src/components/ThemedImage.tsx
  src/components/search/SearchDialog.tsx
  src/components/mdx/*.tsx           VideoEmbed, Steps, Callout, CodeBlock, CodeTabs, UiLabel, RoleBadge, index.ts
  src/layout/SiteHeader.tsx, SiteFooter.tsx, MobileNav.tsx, nav.ts
  src/layout/primitives.tsx          Section, SectionIntro, PageHero, ImageFrame, CheckList, IconBox, FeatureCard, MetricCard
  src/docs/DocPage.tsx, DocsSidebar.tsx, DocsMobileNav.tsx, DocToc.tsx, DocHeader.tsx, DocPager.tsx
  src/pages/HomePage.tsx, ArchitecturePage.tsx, PerformancePage.tsx, ComparisonPage.tsx, NotFoundPage.tsx, shared-content.ts
```

`src/App.css` is deleted in Task 4.

---

# Phase 1 — Foundation

### Task 1: Tooling, tokens, and test setup

**Files:**
- Modify: `package.json`, `vite.config.ts`, `tsconfig.app.json`, `tsconfig.node.json`, `index.html`, `src/index.css`
- Create: `vitest.config.ts`, `src/test/setup.ts`, `src/styles/tokens.css`, `src/lib/utils.ts`, `src/lib/utils.test.ts`, `src/styles/tokens.test.ts`

**Interfaces:**
- Produces: `cn(...inputs: ClassValue[]): string` in `@/lib/utils`; the `@/` import alias for `src/`; Tailwind color utilities `bg-background`, `bg-bg-alt`, `bg-card`, `bg-card-hover`, `text-foreground`, `text-text-bright`, `text-muted-foreground`, `text-text-dim`, `text-primary`, `text-primary-text`, `bg-primary`, `bg-accent-dim`, `border-border`, `border-border-light`, `bg-terminal-bg`, `border-terminal-border`, `text-terminal-text`, `text-terminal-dim`, `text-terminal-accent`, `text-info`, `text-warning`, `text-violet`, `text-destructive`, `shadow-card`, `shadow-card-hover`, `bg-glass`; utility `focus-ring`; `dark:` variant keyed on `.dark`.

- [ ] **Step 1: Install dependencies**

```bash
cd /Users/kasunranasinghe/Projects/FeatureToggle/fluxgate-site
pnpm add tailwindcss@^4.3.3 @tailwindcss/vite@^4.3.3 class-variance-authority@^0.7.1 clsx@^2.1.1 tailwind-merge@^3.7.0 @radix-ui/react-slot@^1.4.0 @radix-ui/react-dialog@^1.2.0 @radix-ui/react-tabs@^1.1.22 @fontsource-variable/dm-sans@^5.3.0 @fontsource-variable/jetbrains-mono@^5.3.0
pnpm add -D vitest@^5.0.3 jsdom@^30.1.2 @testing-library/react@^16.3.3 @testing-library/dom
```

Expected: `pnpm-lock.yaml` updated, no peer dependency errors for `vite@8`.

- [ ] **Step 2: Write the failing tests**

`src/lib/utils.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { cn } from './utils'

describe('cn', () => {
  it('joins truthy classes and drops falsy ones', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c')
  })

  it('lets a later Tailwind class win over a conflicting earlier one', () => {
    expect(cn('px-2 text-sm', 'px-4')).toBe('text-sm px-4')
  })
})
```

`src/styles/tokens.test.ts`:

```ts
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8')

function block(selector: string): string {
  const start = css.indexOf(`${selector} {`)
  expect(start, `${selector} block missing`).toBeGreaterThanOrEqual(0)
  return css.slice(start, css.indexOf('\n}', start))
}

describe('design tokens', () => {
  it('uses the admin UI light palette', () => {
    const light = block(':root')
    expect(light).toContain('--background: #f7f9fc;')
    expect(light).toContain('--primary: #009966;')
    expect(light).toContain('--primary-text: #006644;')
    expect(light).toContain('--terminal-bg: #060b18;')
  })

  it('uses the admin UI dark palette', () => {
    const dark = block('.dark')
    expect(dark).toContain('--background: #060b18;')
    expect(dark).toContain('--card: #0f1629;')
    expect(dark).toContain('--primary: #00e599;')
  })
})
```

- [ ] **Step 3: Add the test runner config**

`vitest.config.ts`:

```ts
import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{ts,tsx}', 'mdx/**/*.test.ts', 'scripts/**/*.test.mjs'],
      setupFiles: ['./src/test/setup.ts'],
    },
  }),
)
```

`src/test/setup.ts`:

```ts
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
  document.documentElement.className = ''
  try {
    window.localStorage.clear()
  } catch {
    // Some tests replace localStorage with a throwing stub.
  }
})
```

Add to `package.json` `scripts`: `"test": "vitest run"`.

- [ ] **Step 4: Run tests to verify they fail**

Run: `pnpm test`
Expected: FAIL — `Cannot find module './utils'` and `ENOENT ... tokens.css`.

- [ ] **Step 5: Wire Vite, TypeScript, and the alias**

`vite.config.ts`:

```ts
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
```

`tsconfig.app.json`: inside `compilerOptions` add `"paths": { "@/*": ["./src/*"] }`, and after `"include"` add `"exclude": ["src/**/*.test.ts", "src/**/*.test.tsx", "src/test"]`. Tests use Node APIs (`node:fs`) that the browser project does not type; Vitest compiles them on its own.

`tsconfig.node.json`: change `"include"` to `["vite.config.ts", "vitest.config.ts", "mdx"]` and add `"exclude": ["mdx/**/*.test.ts"]`.

- [ ] **Step 6: Write `src/lib/utils.ts`**

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 7: Write `src/styles/tokens.css`**

Values are copied from `../feature-toggle-ui/src/index.css` (`:root` core palette, `.dark`, `@theme inline`, `focus-ring`). Legacy aliases are left out on purpose.

```css
:root {
  --font-body: "DM Sans Variable", "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-code: "JetBrains Mono Variable", "JetBrains Mono", ui-monospace, monospace;
  --radius: 0.75rem;

  --background: #f7f9fc;
  --bg-alt: #eef2f7;
  --card: #ffffff;
  --card-hover: #f1f5f9;
  --border: #e2e8f0;
  --border-light: #cbd5e1;
  --foreground: #0b1220;
  --text-bright: #020617;
  --muted-foreground: #475569;
  --text-dim: #5b6b82;
  --primary: #009966;
  --primary-foreground: #060b18;
  --primary-text: #006644;
  --accent-dim: rgba(0, 153, 102, 0.1);
  --accent-glow: rgba(0, 153, 102, 0.22);
  --success: var(--primary-text);
  --info: #075985;
  --violet: #6d28d9;
  --warning: #9a3412;
  --destructive: #a81c1c;
  --destructive-foreground: #ffffff;
  --bg-glass: rgba(247, 249, 252, 0.82);
  --elev-card: 0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
  --elev-card-hover: 0 12px 32px rgba(15, 23, 42, 0.1);
  --overlay: rgba(15, 23, 42, 0.45);

  --terminal-bg: #060b18;
  --terminal-border: #1a2344;
  --terminal-text: #e2e8f0;
  --terminal-dim: #7e8ca6;
  --terminal-accent: #00e599;

  --card-foreground: var(--foreground);
  --popover: var(--card);
  --popover-foreground: var(--foreground);
  --secondary: var(--bg-alt);
  --secondary-foreground: var(--foreground);
  --muted: var(--bg-alt);
  --accent: var(--card-hover);
  --accent-foreground: var(--foreground);
  --input: var(--border-light);
  --ring: var(--primary);
}

.dark {
  color-scheme: dark;
  --background: #060b18;
  --bg-alt: #0c1225;
  --card: #0f1629;
  --card-hover: #151d35;
  --border: #1a2344;
  --border-light: #243056;
  --foreground: #e2e8f0;
  --text-bright: #f8fafc;
  --muted-foreground: #94a3b8;
  --text-dim: #7e8ca6;
  --primary: #00e599;
  --primary-foreground: #060b18;
  --primary-text: #00e599;
  --accent-dim: rgba(0, 229, 153, 0.1);
  --accent-glow: rgba(0, 229, 153, 0.25);
  --success: #00e599;
  --info: #38bdf8;
  --violet: #a78bfa;
  --warning: #fb923c;
  --destructive: #f87171;
  --destructive-foreground: #060b18;
  --bg-glass: rgba(6, 11, 24, 0.82);
  --elev-card: 0 2px 8px rgba(0, 0, 0, 0.35);
  --elev-card-hover: 0 12px 40px rgba(0, 0, 0, 0.5);
  --overlay: rgba(6, 11, 24, 0.7);
}

@utility focus-ring {
  outline-style: none;
  @media (forced-colors: active) {
    outline: 2px solid transparent;
    outline-offset: 2px;
  }
  --tw-ring-shadow: 0 0 0 2px var(--primary), 0 0 0 5px var(--accent-glow);
  box-shadow: var(--tw-inset-shadow), var(--tw-inset-ring-shadow), var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow);
}

@theme inline {
  --font-sans: var(--font-body);
  --font-mono: var(--font-code);
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --shadow-card: var(--elev-card);
  --shadow-card-hover: var(--elev-card-hover);
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-card-hover: var(--card-hover);
  --color-bg-alt: var(--bg-alt);
  --color-glass: var(--bg-glass);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary-text: var(--primary-text);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent-dim: var(--accent-dim);
  --color-accent-glow: var(--accent-glow);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-success: var(--success);
  --color-info: var(--info);
  --color-violet: var(--violet);
  --color-warning: var(--warning);
  --color-border: var(--border);
  --color-border-light: var(--border-light);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-overlay: var(--overlay);
  --color-text-bright: var(--text-bright);
  --color-text-dim: var(--text-dim);
  --color-terminal-bg: var(--terminal-bg);
  --color-terminal-border: var(--terminal-border);
  --color-terminal-text: var(--terminal-text);
  --color-terminal-dim: var(--terminal-dim);
  --color-terminal-accent: var(--terminal-accent);
}
```

- [ ] **Step 8: Replace `src/index.css`**

The old dark palette in `src/index.css` is replaced. `src/App.css` still exists and still renders until Task 4; its old variables become undefined, which is expected inside Phase 1.

```css
@import "tailwindcss";
@import "@fontsource-variable/dm-sans";
@import "@fontsource-variable/jetbrains-mono";
@import "./styles/tokens.css";

@custom-variant dark (&:is(.dark *));

html {
  scroll-behavior: smooth;
  -webkit-text-size-adjust: 100%;
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

body {
  margin: 0;
  min-width: 320px;
  font-family: var(--font-body);
  line-height: 1.5;
  color: var(--foreground);
  background: var(--background);
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  color: inherit;
}
```

- [ ] **Step 9: Drop Google Fonts from `index.html`**

Delete the two `<link rel="preconnect" ...>` lines and the `fonts.googleapis.com` stylesheet `<link>`. Fonts now come from `@fontsource-variable/*` bundled by Vite.

- [ ] **Step 10: Run tests, lint, and build**

Run: `pnpm test && pnpm lint && pnpm build`
Expected: tests PASS (4 tests); lint clean; build writes `dist/` (pages look unstyled where they used old variables; that is fixed in Tasks 3–4).

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "build: add Tailwind v4, admin UI tokens, and Vitest

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: UI primitives and theme

**Files:**
- Create: `src/components/ui/button.tsx`, `card.tsx`, `badge.tsx`, `eyebrow.tsx`, `kbd.tsx`, `terminal-block.tsx`, `src/theme/theme.ts`, `src/theme/theme.test.ts`, `src/theme/inline-script.test.ts`, `src/components/ThemeToggle.tsx`, `src/components/ThemeToggle.test.tsx`, `src/components/ThemedImage.tsx`
- Modify: `index.html`

**Interfaces:**
- Consumes: `cn` (Task 1).
- Produces:
  - `Button` (props: `variant?: 'default'|'destructive'|'outline'|'secondary'|'ghost'|'link'`, `size?: 'default'|'sm'|'lg'|'icon'`, `asChild?: boolean`, plus button props).
  - `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` (`Card` takes `interactive?: boolean`).
  - `Badge` (`variant?: 'default'|'secondary'|'outline'|'success'|'warning'|'info'|'error'`).
  - `Eyebrow`, `Kbd`.
  - `TerminalBlock({ title?: string; copyable?: boolean; className?: string; children: ReactNode })` — renders its children inside the terminal chrome; the copy button copies the text content of the `<pre>` inside it.
  - `type ThemeName = 'light' | 'dark'`, `THEME_STORAGE_KEY = 'fluxgate-site-theme'`, `resolveTheme(stored: string | null, prefersDark: boolean): ThemeName`, `readStoredTheme(): string | null`, `writeStoredTheme(theme: ThemeName): void`, `applyTheme(theme: ThemeName, root?: HTMLElement): void`, `currentTheme(root?: HTMLElement): ThemeName`.
  - `ThemeToggle({ className?: string })`.
  - `ThemedImage({ light: string; dark: string; alt: string; className?: string; width?: number; height?: number })`.

- [ ] **Step 1: Write the failing theme tests**

`src/theme/theme.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { applyTheme, currentTheme, readStoredTheme, resolveTheme, writeStoredTheme, THEME_STORAGE_KEY } from './theme'

afterEach(() => vi.restoreAllMocks())

describe('resolveTheme', () => {
  it('prefers a stored choice', () => {
    expect(resolveTheme('dark', false)).toBe('dark')
    expect(resolveTheme('light', true)).toBe('light')
  })

  it('falls back to the OS preference for missing or unknown values', () => {
    expect(resolveTheme(null, true)).toBe('dark')
    expect(resolveTheme(null, false)).toBe('light')
    expect(resolveTheme('purple', true)).toBe('dark')
  })
})

describe('storage helpers', () => {
  it('round-trips the stored theme', () => {
    writeStoredTheme('dark')
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    expect(readStoredTheme()).toBe('dark')
  })

  it('survives storage that throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(readStoredTheme()).toBeNull()
    expect(() => writeStoredTheme('light')).not.toThrow()
  })
})

describe('applyTheme', () => {
  it('toggles the dark class on the root element', () => {
    applyTheme('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(currentTheme()).toBe('dark')
    applyTheme('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(currentTheme()).toBe('light')
  })
})
```

`src/theme/inline-script.test.ts` (keeps the pre-paint script in `index.html` in step with `resolveTheme`):

```ts
import { readFileSync } from 'node:fs'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveTheme, THEME_STORAGE_KEY } from './theme'

const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8')
const inline = html.match(/<script>([\s\S]*?)<\/script>/)?.[1] ?? ''

function runScript(prefersDark: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({ matches: prefersDark }) as unknown as typeof window.matchMedia
  document.documentElement.className = ''
  new Function(inline)()
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

afterEach(() => vi.restoreAllMocks())

describe('index.html theme script', () => {
  it('exists', () => {
    expect(inline).toContain(THEME_STORAGE_KEY)
  })

  for (const stored of [null, 'light', 'dark']) {
    for (const prefersDark of [false, true]) {
      it(`matches resolveTheme for stored=${stored} prefersDark=${prefersDark}`, () => {
        if (stored) window.localStorage.setItem(THEME_STORAGE_KEY, stored)
        expect(runScript(prefersDark)).toBe(resolveTheme(stored, prefersDark))
      })
    }
  }

  it('does not throw when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(runScript(true)).toBe('dark')
  })
})
```

`src/components/ThemeToggle.test.tsx`:

```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { renderToString } from 'react-dom/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeToggle } from './ThemeToggle'
import { THEME_STORAGE_KEY } from '@/theme/theme'

beforeEach(() => {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }) as unknown as typeof window.matchMedia
})

describe('ThemeToggle', () => {
  it('switches light to dark and stores the choice', () => {
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: 'Toggle color theme' }))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    fireEvent.click(screen.getByRole('button', { name: 'Toggle color theme' }))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')
  })

  it('renders the same markup whatever the current theme', () => {
    const light = renderToString(<ThemeToggle />)
    document.documentElement.classList.add('dark')
    const dark = renderToString(<ThemeToggle />)
    expect(dark).toBe(light)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test src/theme src/components/ThemeToggle.test.tsx`
Expected: FAIL — modules `./theme` and `./ThemeToggle` not found; inline script test fails `exists`.

- [ ] **Step 3: Write `src/theme/theme.ts`**

```ts
export type ThemeName = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'fluxgate-site-theme'

export function resolveTheme(stored: string | null, prefersDark: boolean): ThemeName {
  if (stored === 'light' || stored === 'dark') return stored
  return prefersDark ? 'dark' : 'light'
}

export function readStoredTheme(): string | null {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY)
  } catch {
    return null
  }
}

export function writeStoredTheme(theme: ThemeName): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Storage blocked: the theme still applies to this page view.
  }
}

export function applyTheme(theme: ThemeName, root: HTMLElement = document.documentElement): void {
  root.classList.toggle('dark', theme === 'dark')
}

export function currentTheme(root: HTMLElement = document.documentElement): ThemeName {
  return root.classList.contains('dark') ? 'dark' : 'light'
}
```

- [ ] **Step 4: Add the pre-paint script and theme colors to `index.html`**

Replace `<meta name="theme-color" content="#0a0e16" />` with:

```html
    <meta name="theme-color" content="#f7f9fc" media="(prefers-color-scheme: light)" />
    <meta name="theme-color" content="#060b18" media="(prefers-color-scheme: dark)" />
    <script>
      (function () {
        var stored = null
        try {
          stored = window.localStorage.getItem('fluxgate-site-theme')
        } catch (e) {}
        var dark = stored === 'dark' || (stored !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches)
        if (dark) document.documentElement.classList.add('dark')
      })()
    </script>
```

This must be the only `<script>` tag without a `src` attribute in `index.html` (the test reads the first one).

- [ ] **Step 5: Copy the UI primitives**

Copy these files from `../feature-toggle-ui/src/components/ui/` into `src/components/ui/` unchanged except for formatting: `button.tsx`, `card.tsx`, `badge.tsx`, `eyebrow.tsx`, `kbd.tsx`. In `button.tsx` delete the `info` variant (unused). All imports already use `@/lib/utils`.

Write `src/components/ui/terminal-block.tsx` (adapted: children instead of a `code` string, no toast library):

```tsx
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TerminalBlockProps {
  title?: string
  copyable?: boolean
  className?: string
  children: ReactNode
}

export function TerminalBlock({ title, copyable = true, className, children }: TerminalBlockProps) {
  const [copied, setCopied] = useState(false)
  const body = useRef<HTMLDivElement>(null)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  const handleCopy = async () => {
    const text = body.current?.querySelector('pre')?.textContent ?? body.current?.textContent ?? ''
    try {
      await navigator.clipboard.writeText(text.replace(/\n$/, ''))
      setCopied(true)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div
      data-slot="terminal-block"
      className={cn('my-5 overflow-hidden rounded-lg border border-terminal-border bg-terminal-bg text-terminal-text', className)}
    >
      <div className="flex items-center gap-3 border-b border-terminal-border px-3 py-2">
        <span aria-hidden className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-terminal-border" />
          <span className="h-2.5 w-2.5 rounded-full bg-terminal-border" />
          <span className="h-2.5 w-2.5 rounded-full bg-terminal-border" />
        </span>
        {title && <span className="truncate font-mono text-xs text-terminal-dim">{title}</span>}
        {copyable && (
          <button
            type="button"
            onClick={handleCopy}
            aria-label={title ? `Copy ${title}` : 'Copy code'}
            className="ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[11px] text-terminal-dim transition-colors hover:text-terminal-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terminal-accent"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            <span aria-live="polite">{copied ? 'Copied' : 'Copy'}</span>
          </button>
        )}
      </div>
      <div ref={body} className="terminal-body">
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Write `ThemeToggle` and `ThemedImage`**

`src/components/ThemeToggle.tsx`:

```tsx
import { useEffect } from 'react'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { applyTheme, currentTheme, readStoredTheme, writeStoredTheme } from '@/theme/theme'

export function ThemeToggle({ className }: { className?: string }) {
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const follow = () => {
      if (readStoredTheme() === null) applyTheme(media.matches ? 'dark' : 'light')
    }
    media.addEventListener('change', follow)
    return () => media.removeEventListener('change', follow)
  }, [])

  const toggle = () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark'
    applyTheme(next)
    writeStoredTheme(next)
  }

  // Both icons render; CSS picks one, so server and client markup always match.
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle color theme" className={className}>
      <Moon className="dark:hidden" aria-hidden="true" />
      <Sun className="hidden dark:block" aria-hidden="true" />
    </Button>
  )
}
```

`src/components/ThemedImage.tsx`:

```tsx
import { cn } from '@/lib/utils'

interface ThemedImageProps {
  light: string
  dark: string
  alt: string
  className?: string
  width?: number
  height?: number
}

export function ThemedImage({ light, dark, alt, className, width, height }: ThemedImageProps) {
  return (
    <>
      <img src={light} alt={alt} width={width} height={height} loading="lazy" className={cn('dark:hidden', className)} />
      <img src={dark} alt={alt} width={width} height={height} loading="lazy" className={cn('hidden dark:block', className)} />
    </>
  )
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pnpm test`
Expected: PASS (all theme, inline script, toggle, utils, token tests).

- [ ] **Step 8: Lint and commit**

Run: `pnpm lint` (warnings from `react-refresh/only-export-components` on `button.tsx`/`badge.tsx` are acceptable; errors are not).

```bash
git add -A
git commit -m "feat: add admin UI primitives and light/dark theme

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Site shell and layout primitives

**Files:**
- Create: `src/lib/paths.ts`, `src/lib/paths.test.ts`, `src/layout/nav.ts`, `src/layout/SiteHeader.tsx`, `src/layout/MobileNav.tsx`, `src/layout/SiteFooter.tsx`, `src/layout/SiteHeader.test.tsx`, `src/layout/primitives.tsx`
- Modify: `src/App.tsx` (replace `Header`, `Footer`, `site-shell` wrapper), `src/site.ts` (remove `normalizePath`)

**Interfaces:**
- Consumes: `Button`, `ThemeToggle`, `Eyebrow`, `Card`, `cn`.
- Produces:
  - `normalizePath(path: string): string` in `@/lib/paths` — strips query and hash, strips a trailing `index.html`, ensures a leading and a trailing slash, collapses repeated slashes.
  - `navItems: Array<{ href: string; label: string }>`, `isActiveNav(href: string, path: string): boolean` in `@/layout/nav`.
  - `SiteHeader({ path: string; searchSlot?: ReactNode })`, `SiteFooter()`, `MobileNav({ path: string })`.
  - In `@/layout/primitives`: `Section({ tone?: 'base'|'alt'; id?: string; className?: string; children })`, `Container({ className?: string; children })`, `SectionIntro({ eyebrow: string; title: string; text?: string; align?: 'left'|'center' })`, `PageHero({ eyebrow: string; title: string; text: string; breadcrumb: string; image?: { src: string; alt: string } })`, `ImageFrame({ src: string; alt: string; caption?: string })`, `CheckList({ items: string[] })`, `IconBox({ icon: LucideIcon })`, `FeatureCard({ icon: LucideIcon; title: string; text: string })`, `MetricCard({ label: string; value: string })`.

- [ ] **Step 1: Write the failing tests**

`src/lib/paths.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { normalizePath } from './paths'

describe('normalizePath', () => {
  it.each([
    ['/', '/'],
    ['', '/'],
    ['/docs', '/docs/'],
    ['/docs/', '/docs/'],
    ['/docs/get-started/install', '/docs/get-started/install/'],
    ['/docs/get-started/install/index.html', '/docs/get-started/install/'],
    ['/index.html', '/'],
    ['/performance/?utm=x#top', '/performance/'],
    ['//docs//contexts', '/docs/contexts/'],
  ])('%s -> %s', (input, expected) => {
    expect(normalizePath(input)).toBe(expected)
  })
})
```

`src/layout/SiteHeader.test.tsx`:

```tsx
import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SiteHeader } from './SiteHeader'
import { isActiveNav } from './nav'

beforeEach(() => {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }) as unknown as typeof window.matchMedia
})

describe('isActiveNav', () => {
  it('matches home only on /', () => {
    expect(isActiveNav('/', '/')).toBe(true)
    expect(isActiveNav('/', '/docs/')).toBe(false)
  })

  it('matches sections by prefix', () => {
    expect(isActiveNav('/docs/', '/docs/get-started/install/')).toBe(true)
    expect(isActiveNav('/performance/', '/docs/')).toBe(false)
  })
})

describe('SiteHeader', () => {
  it('renders primary navigation and marks the active item', () => {
    render(<SiteHeader path="/docs/get-started/install/" />)
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    for (const label of ['Product', 'Docs', 'Architecture', 'Performance', 'Comparison']) {
      expect(within(nav).getByRole('link', { name: label })).toBeTruthy()
    }
    expect(within(nav).getByRole('link', { name: 'Docs' }).getAttribute('aria-current')).toBe('page')
    expect(screen.getByRole('link', { name: 'Get started' }).getAttribute('href')).toBe('/docs/get-started/install/')
    expect(screen.getByRole('button', { name: 'Open menu' })).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test src/lib/paths.test.ts src/layout`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write `src/lib/paths.ts`**

```ts
export function normalizePath(path: string): string {
  let pathname = path.split(/[?#]/)[0] ?? ''
  pathname = pathname.replace(/\/{2,}/g, '/').replace(/index\.html$/, '')
  if (!pathname.startsWith('/')) pathname = `/${pathname}`
  if (!pathname.endsWith('/')) pathname = `${pathname}/`
  return pathname
}
```

In `src/site.ts`, delete the old `normalizePath` function. In `src/App.tsx`, import `normalizePath` from `@/lib/paths` instead of `./site`. Keep `getRouteMeta` in `site.ts` working for now by changing its body to:

```ts
export function getRouteMeta(path: string): RouteMeta {
  const routePath = normalizePath(path)
  return routes.find((route) => route.path === routePath) ?? routes[0]
}
```

with `import { normalizePath } from './lib/paths'` at the top of `site.ts`.

- [ ] **Step 4: Write `src/layout/nav.ts`**

```ts
export const navItems = [
  { href: '/', label: 'Product' },
  { href: '/docs/', label: 'Docs' },
  { href: '/architecture/', label: 'Architecture' },
  { href: '/performance/', label: 'Performance' },
  { href: '/comparison/', label: 'Comparison' },
]

export const GET_STARTED_HREF = '/docs/get-started/install/'

export function isActiveNav(href: string, path: string): boolean {
  return href === '/' ? path === '/' : path.startsWith(href)
}
```

- [ ] **Step 5: Write `SiteHeader` and `MobileNav`**

`src/layout/SiteHeader.tsx`:

```tsx
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'
import { GITHUB_REPO, PRODUCT_ICON } from '@/site'
import { MobileNav } from './MobileNav'
import { GET_STARTED_HREF, isActiveNav, navItems } from './nav'

// lucide-react 1.x ships no brand icons, so the GitHub mark is inline.
function GithubMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
      <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a10.9 10.9 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  )
}

export function SiteHeader({ path, searchSlot }: { path: string; searchSlot?: ReactNode }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-glass backdrop-blur-md backdrop-saturate-150">
      <div className="mx-auto flex h-16 w-full max-w-[1400px] items-center gap-4 px-4 sm:px-6">
        <a href="/" className="flex shrink-0 items-center gap-2 font-semibold text-text-bright no-underline">
          <img src={PRODUCT_ICON} alt="" width={28} height={28} className="h-7 w-7" />
          <span>FluxGate</span>
        </a>
        <nav aria-label="Primary" className="ml-4 hidden items-center gap-1 lg:flex">
          {navItems.map((item) => {
            const active = isActiveNav(item.href, path)
            return (
              <a
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'rounded-md px-3 py-2 text-sm font-medium no-underline transition-colors focus-visible:focus-ring',
                  active ? 'bg-accent-dim text-text-bright' : 'text-muted-foreground hover:bg-card-hover hover:text-foreground',
                )}
              >
                {item.label}
              </a>
            )
          })}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          {searchSlot}
          <Button variant="ghost" size="icon" asChild className="hidden sm:inline-flex">
            <a href={GITHUB_REPO} target="_blank" rel="noreferrer" aria-label="FluxGate on GitHub">
              <GithubMark />
            </a>
          </Button>
          <ThemeToggle />
          <Button asChild size="sm" className="ml-2 hidden sm:inline-flex">
            <a href={GET_STARTED_HREF}>Get started</a>
          </Button>
          <MobileNav path={path} />
        </div>
      </div>
    </header>
  )
}
```

`src/layout/MobileNav.tsx`:

```tsx
import * as Dialog from '@radix-ui/react-dialog'
import { Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { GET_STARTED_HREF, isActiveNav, navItems } from './nav'

export function MobileNav({ path }: { path: string }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <Button variant="ghost" size="icon" aria-label="Open menu" className="lg:hidden">
          <Menu aria-hidden="true" />
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-overlay" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-[min(320px,85vw)] flex-col gap-2 border-l border-border bg-card p-4 shadow-card-hover">
          <div className="flex items-center justify-between">
            <Dialog.Title className="text-sm font-semibold text-text-bright">Menu</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close menu">
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">Site navigation</Dialog.Description>
          <nav aria-label="Mobile" className="flex flex-col gap-1">
            {navItems.map((item) => {
              const active = isActiveNav(item.href, path)
              return (
                <a
                  key={item.href}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex h-10 items-center rounded-md px-3 text-sm font-medium no-underline',
                    active ? 'bg-accent-dim text-text-bright' : 'text-muted-foreground hover:bg-card-hover hover:text-foreground',
                  )}
                >
                  {item.label}
                </a>
              )
            })}
          </nav>
          <Button asChild className="mt-2">
            <a href={GET_STARTED_HREF}>Get started</a>
          </Button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
```

- [ ] **Step 6: Write `SiteFooter`**

`src/layout/SiteFooter.tsx`:

```tsx
import { CONTACT_EMAIL, FORGEOPS_LOGO, GITHUB_REPO, MAIN_SITE_URL, PRODUCT_ICON } from '@/site'

const columns = [
  {
    title: 'Product',
    links: [
      { href: '/', label: 'Overview' },
      { href: '/architecture/', label: 'Architecture' },
      { href: '/performance/', label: 'Performance' },
      { href: '/comparison/', label: 'Comparison' },
    ],
  },
  {
    title: 'Docs',
    links: [
      { href: '/docs/', label: 'Documentation' },
      { href: '/docs/developer-guide/', label: 'Developer guide' },
      { href: '/docs/get-started/install/', label: 'Install' },
      { href: '/docs/reference/edge-api/', label: 'Edge API' },
    ],
  },
  {
    title: 'Company',
    links: [
      { href: MAIN_SITE_URL, label: 'ForgeOps LABS' },
      { href: GITHUB_REPO, label: 'GitHub' },
      { href: `mailto:${CONTACT_EMAIL}`, label: CONTACT_EMAIL },
    ],
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-bg-alt">
      <div className="mx-auto grid w-full max-w-[1400px] gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.5fr_repeat(3,1fr)]">
        <div className="flex flex-col gap-3">
          <a href="/" className="flex items-center gap-2 font-semibold text-text-bright no-underline">
            <img src={PRODUCT_ICON} alt="" width={28} height={28} className="h-7 w-7" />
            FluxGate
          </a>
          <p className="max-w-xs text-sm text-muted-foreground">
            Feature flag delivery with governed rollouts, edge evaluation, and OpenFeature-ready integrations.
          </p>
          <a href={MAIN_SITE_URL} className="mt-2 inline-flex items-center gap-2 text-xs text-text-dim no-underline">
            <img src={FORGEOPS_LOGO} alt="ForgeOps LABS" className="h-5 w-auto" />
          </a>
        </div>
        {columns.map((column) => (
          <div key={column.title}>
            <p className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-text-dim">{column.title}</p>
            <ul className="flex flex-col gap-2 text-sm">
              {column.links.map((link) => (
                <li key={link.href}>
                  <a href={link.href} className="break-all text-muted-foreground no-underline hover:text-foreground">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border py-4 text-center text-xs text-text-dim">© {new Date().getFullYear()} ForgeOps LABS</div>
    </footer>
  )
}
```

- [ ] **Step 7: Write the layout primitives**

`src/layout/primitives.tsx`:

```tsx
import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { CheckCircle2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import { cn } from '@/lib/utils'

export function Container({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('mx-auto w-full max-w-[1180px] px-4 sm:px-6', className)}>{children}</div>
}

export function Section({
  tone = 'base',
  id,
  className,
  children,
}: {
  tone?: 'base' | 'alt'
  id?: string
  className?: string
  children: ReactNode
}) {
  return (
    <section id={id} className={cn('py-16 sm:py-20', tone === 'alt' ? 'bg-bg-alt' : 'bg-background', className)}>
      <Container>{children}</Container>
    </section>
  )
}

export function SectionIntro({
  eyebrow,
  title,
  text,
  align = 'left',
}: {
  eyebrow: string
  title: string
  text?: string
  align?: 'left' | 'center'
}) {
  return (
    <div className={cn('mb-10 max-w-2xl', align === 'center' && 'mx-auto text-center')}>
      <Eyebrow className="mb-3 text-primary-text">{eyebrow}</Eyebrow>
      <h2 className="text-3xl font-semibold tracking-[-0.02em] text-text-bright sm:text-4xl">{title}</h2>
      {text && <p className="mt-4 text-lg text-muted-foreground">{text}</p>}
    </div>
  )
}

export function PageHero({
  eyebrow,
  title,
  text,
  breadcrumb,
  image,
}: {
  eyebrow: string
  title: string
  text: string
  breadcrumb: string
  image?: { src: string; alt: string }
}) {
  return (
    <section className="relative overflow-hidden border-b border-border bg-background">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 right-0 h-[480px] w-[640px] rounded-full bg-accent-glow opacity-60 blur-3xl"
      />
      <Container className="relative grid gap-10 py-16 sm:py-20 lg:grid-cols-[1.1fr_1fr] lg:items-center">
        <div>
          <nav aria-label="Breadcrumb" className="mb-4 text-sm text-text-dim">
            <a href="/" className="no-underline hover:text-foreground">FluxGate</a>
            <span aria-hidden="true"> / </span>
            <span aria-current="page">{breadcrumb}</span>
          </nav>
          <Eyebrow className="mb-3 text-primary-text">{eyebrow}</Eyebrow>
          <h1 className="text-4xl font-semibold tracking-[-0.02em] text-text-bright sm:text-5xl">{title}</h1>
          <p className="mt-5 max-w-xl text-lg text-muted-foreground">{text}</p>
        </div>
        {image && <ImageFrame src={image.src} alt={image.alt} />}
      </Container>
    </section>
  )
}

export function ImageFrame({ src, alt, caption }: { src: string; alt: string; caption?: string }) {
  return (
    <figure className="m-0 overflow-hidden rounded-xl border border-border bg-card shadow-card">
      <img src={src} alt={alt} loading="lazy" className="block h-auto w-full" />
      {caption && <figcaption className="border-t border-border px-4 py-3 text-sm text-muted-foreground">{caption}</figcaption>}
    </figure>
  )
}

export function CheckList({ items }: { items: string[] }) {
  return (
    <ul className="mt-6 flex flex-col gap-3">
      {items.map((item) => (
        <li key={item} className="flex gap-3 text-muted-foreground">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function IconBox({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-accent-dim text-primary-text">
      <Icon className="h-5 w-5" aria-hidden="true" />
    </span>
  )
}

export function FeatureCard({ icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return (
    <Card className="flex flex-col gap-3 p-6">
      <IconBox icon={icon} />
      <h3 className="text-base font-semibold text-text-bright">{title}</h3>
      <p className="text-sm text-muted-foreground">{text}</p>
    </Card>
  )
}

export function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="flex flex-col gap-1 p-5">
      <strong className="font-mono text-2xl font-semibold text-text-bright">{value}</strong>
      <span className="text-sm text-muted-foreground">{label}</span>
    </Card>
  )
}
```

- [ ] **Step 8: Use the new shell in `App.tsx`**

In `src/App.tsx`: delete the local `Header` and `Footer` functions, import `SiteHeader` and `SiteFooter`, and replace the `App` body with:

```tsx
function App({ path = '/' }: { path?: string }) {
  const routePath = normalizePath(path)

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-4 focus:py-2 focus:shadow-card-hover"
      >
        Skip to content
      </a>
      <SiteHeader path={routePath} />
      <main id="main" className="flex-1">
        {routePath === '/' && <HomePage />}
        {routePath === '/architecture/' && <ArchitecturePage />}
        {routePath === '/performance/' && <PerformancePage />}
        {routePath === '/comparison/' && <ComparisonPage />}
      </main>
      <SiteFooter />
    </div>
  )
}
```

Remove the now-unused `navItems` constant and the `Mail` import from `App.tsx`.

- [ ] **Step 9: Run tests, lint, and build**

Run: `pnpm test && pnpm lint && pnpm build`
Expected: all PASS; build succeeds.

- [ ] **Step 10: Check the shell in the browser**

Run `pnpm dev`, open `http://localhost:5173/` in the built-in browser. Check: header is sticky with glass background; theme toggle switches light/dark with no flash on reload; at 375 px the nav collapses into the "Open menu" drawer; no horizontal scroll.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: new site header, footer, and layout primitives

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Port the product pages and remove the old stylesheet

**Files:**
- Create: `src/pages/shared-content.ts`, `src/pages/HomePage.tsx`, `src/pages/ArchitecturePage.tsx`, `src/pages/PerformancePage.tsx`, `src/pages/ComparisonPage.tsx`, `src/pages/NotFoundPage.tsx`, `src/pages/pages.test.tsx`
- Modify: `src/App.tsx`
- Delete: `src/App.css`

**Interfaces:**
- Consumes: layout primitives (Task 3), `Button`, `Card`, `Eyebrow`.
- Produces: `HomePage()`, `ArchitecturePage()`, `PerformancePage()`, `ComparisonPage()`, `NotFoundPage()`; `shared-content.ts` exports the data arrays `proofStats`, `features`, `screenshots`, `architectureSteps`, `comparisonRows`, `faqs` (moved verbatim from `App.tsx`), plus `ArchitectureDiagram()` exported from `ArchitecturePage.tsx`.

The page copy stays the same. Only the markup changes. Use this mapping for every legacy class; no class from `App.css` may remain.

| Legacy markup | New markup |
|---|---|
| `<section className="section section-light">` + `<div className="section-inner">` | `<Section>` |
| `section-warm`, `section-accent`, `section-contact` | `<Section tone="alt">` |
| `section-ink` | `<Section tone="alt">` (no dark band; the site follows the theme) |
| `section-inner split-layout`, `media-feature`, `diagram-layout`, `comparison-preview`, `contact-layout` | `<div className="grid gap-10 lg:grid-cols-2 lg:items-center">` inside `<Section>` |
| `section-intro` / `SectionIntro` | `<SectionIntro eyebrow title text />` |
| `<p className="eyebrow">` | `<Eyebrow className="mb-3 text-primary-text">` |
| `page-hero` + `page-hero-grid` + `breadcrumb` + `page-hero-image` | `<PageHero eyebrow title text breadcrumb image />` |
| `image-frame` | `<ImageFrame src alt caption />` |
| `check-list` | `<CheckList items={[...]} />` |
| `icon-box` | `<IconBox icon={Icon} />` |
| `feature-grid`, `feature-grid-tight` | `<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">` |
| `feature-card`, `feature-card-dark` | `<FeatureCard icon title text />` |
| `step-grid` | `<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">` |
| `step-card` + `step-number` | `<Card className="relative flex flex-col gap-3 p-6">` with `<span className="font-mono text-xs text-text-dim">0{index + 1}</span>` |
| `perf-grid`, `proof-grid` | `<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">` |
| `metric-card` | `<MetricCard label value />` |
| `chart-grid`, `screenshot-grid` | `<div className="grid gap-6 md:grid-cols-2">` |
| `screenshot-card` | `<ImageFrame src alt caption={title + ': ' + text} />` |
| `faq-grid` + `faq-item` | `<div className="grid gap-4 md:grid-cols-3">` + `<Card className="p-6"><h3 className="font-semibold text-text-bright">…</h3><p className="mt-2 text-sm text-muted-foreground">…</p></Card>` |
| `comparison-table` / `comparison-row` / `comparison-head` | `<div role="table" className="overflow-hidden rounded-xl border border-border">`, rows `<div role="row" className="grid gap-4 border-b border-border p-5 last:border-b-0 md:grid-cols-[1fr_1.2fr_1.2fr]">`, head row adds `bg-bg-alt font-mono text-[11px] uppercase tracking-[0.08em] text-text-dim` |
| `comparison-points` | `<CheckList items />` |
| `button button-primary` | `<Button asChild><a href>…</a></Button>` |
| `button button-secondary ...` | `<Button asChild variant="secondary"><a href>…</a></Button>` |
| `button-row`, `contact-actions` | `<div className="mt-8 flex flex-wrap gap-3">` |
| `text-link`, `link-on-ink` | `<a className="inline-flex items-center gap-1 font-semibold text-primary-text no-underline hover:underline">` |
| `hero-section` / `hero-bg` / `hero-overlay` / `hero-inner` / `hero-copy` | `<PageHero eyebrow="Feature flag delivery platform" title="FluxGate" text={…} breadcrumb="Product" image={{ src: '/images/system-overview.jpg', alt: 'FluxGate system overview' }} />` followed by the two hero buttons in a `<Container>` (the home hero is rewritten in Task 23) |
| `proof-bar` + `proof-item` | `<Section tone="alt">` + grid of `<MetricCard label value />` |
| `architecture-diagram` + `diagram-node` + `diagram-line` + `diagram-badge` | `ArchitectureDiagram` below |

`ArchitectureDiagram` (in `ArchitecturePage.tsx`, exported for the home page):

```tsx
const nodes = [
  { title: 'React UI', detail: 'REST + WebSocket' },
  { title: 'Rust backend', detail: 'Postgres + gRPC' },
  { title: 'Rust edge', detail: 'cached evaluation' },
  { title: 'Apps + SDKs', detail: 'REST / OFREP' },
]

export function ArchitectureDiagram() {
  return (
    <figure aria-label="FluxGate architecture diagram" className="m-0 rounded-xl border border-border bg-card p-6 shadow-card">
      <ol className="grid gap-3 sm:grid-cols-4">
        {nodes.map((node, index) => (
          <li key={node.title} className="relative flex flex-col gap-1 rounded-lg border border-border bg-bg-alt p-4">
            <span className="font-semibold text-text-bright">{node.title}</span>
            <small className="font-mono text-xs text-text-dim">{node.detail}</small>
            {index < nodes.length - 1 && (
              <span aria-hidden="true" className="absolute -right-2.5 top-1/2 hidden h-px w-2 bg-primary sm:block" />
            )}
          </li>
        ))}
      </ol>
      <figcaption className="mt-4 inline-flex rounded-full bg-accent-dim px-3 py-1 font-mono text-xs text-primary-text">
        telemetry returns to dashboards
      </figcaption>
    </figure>
  )
}
```

- [ ] **Step 1: Write the failing page test**

`src/pages/pages.test.tsx`:

```tsx
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { HomePage } from './HomePage'
import { ArchitecturePage } from './ArchitecturePage'
import { PerformancePage } from './PerformancePage'
import { ComparisonPage } from './ComparisonPage'

const legacy = /class="(section|section-inner|eyebrow|feature-card|image-frame|button|check-list|comparison-row|page-hero)[" ]/

describe.each([
  ['home', HomePage, 'FluxGate'],
  ['architecture', ArchitecturePage, 'FluxGate'],
  ['performance', PerformancePage, 'FluxGate'],
  ['comparison', ComparisonPage, 'FluxGate'],
])('%s page', (_name, Page, heading) => {
  it('renders with new markup only', () => {
    const html = renderToString(<Page />)
    expect(html).toContain(heading)
    expect(html).toMatch(/<h1[ >]/)
    expect(html).not.toMatch(legacy)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm test src/pages`
Expected: FAIL — `./HomePage` not found.

- [ ] **Step 3: Move the data arrays**

Move `proofStats`, `features`, `screenshots`, `architectureSteps`, `comparisonRows`, `faqs` from `src/App.tsx` into `src/pages/shared-content.ts` unchanged, each with `export const`. Keep their `lucide-react` icon imports in that file.

- [ ] **Step 4: Port each page**

Create one file per page. Move each page function out of `App.tsx` (`HomePage` with its sections `Hero`, `ProofBar`, `FeatureSection`, `ScreenshotSection`, `ArchitecturePreview`, `PerformancePreview`, `ComparisonPreview`, `FaqSection`, `ContactBand`; `ArchitecturePage`; `PerformancePage`; `ComparisonPage`), export it by name, and rewrite its markup with the mapping table. Keep every heading, paragraph, list item, image path, and link target as it is. Each page's top element is a `PageHero` so each page has exactly one `<h1>`.

`src/pages/NotFoundPage.tsx`:

```tsx
import { Button } from '@/components/ui/button'
import { Section } from '@/layout/primitives'

export function NotFoundPage() {
  return (
    <Section>
      <div className="mx-auto max-w-xl py-16 text-center">
        <p className="font-mono text-sm text-text-dim">404</p>
        <h1 className="mt-2 text-3xl font-semibold text-text-bright">Page not found</h1>
        <p className="mt-4 text-muted-foreground">The page moved or never existed. Start from the docs or the product overview.</p>
        <div className="mt-8 flex justify-center gap-3">
          <Button asChild><a href="/docs/">Read the docs</a></Button>
          <Button asChild variant="secondary"><a href="/">Product overview</a></Button>
        </div>
      </div>
    </Section>
  )
}
```

- [ ] **Step 5: Slim `App.tsx` and delete `App.css`**

`App.tsx` keeps only `App` (from Task 3 Step 8), imports the four pages from `./pages/*`, renders `<NotFoundPage />` when `routePath` matches none of the four paths, and no longer imports `./App.css`. Delete `src/App.css`.

- [ ] **Step 6: Run tests, lint, and build**

Run: `pnpm test && pnpm lint && pnpm build`
Expected: PASS; `dist/index.html`, `dist/architecture/index.html`, `dist/performance/index.html`, `dist/comparison/index.html` exist.

- [ ] **Step 7: Check all four pages in the browser**

`pnpm preview`, open each page in the built-in browser at 1440 px and 375 px, light and dark. Check: no unstyled block, no horizontal scroll, images load, cards readable in both themes.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: restyle product pages with the admin UI design system

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Phase 1 is complete: the site builds and can be deployed.

---
# Phase 2 — Docs engine

### Task 5: MDX pipeline, frontmatter module, and table of contents

**Files:**
- Create: `mdx/remark-export-toc.ts`, `mdx/remark-export-toc.test.ts`, `mdx/doc-frontmatter-plugin.ts`, `mdx/doc-frontmatter-plugin.test.ts`, `mdx/mdx-options.ts`, `src/virtual.d.ts`, `src/styles/doc-prose.css`, `src/test/fixtures/sample.mdx`, `src/test/mdx-pipeline.test.tsx`
- Modify: `vite.config.ts`, `src/index.css`, `package.json`

**Interfaces:**
- Produces:
  - `type TocEntry = { depth: 2 | 3; text: string; id: string }` and `remarkExportToc()` — every compiled MDX module exports `toc: TocEntry[]`.
  - `readDocFrontmatter(docsDir: string): Record<string, unknown>` — keys are `./docs/<relative path>.mdx`, values are the parsed YAML (or `null` when a file has no frontmatter).
  - `docFrontmatterPlugin(docsDir: string): Plugin` — serves `virtual:doc-frontmatter` (default export: the record above).
  - `mdxOptions` (the remark/rehype config shared by Vite and tests). Code blocks get `data-title` (from a `title="..."` meta) and `data-language` attributes on `<pre>`.
  - CSS class `doc-prose` for MDX articles; `doc-steps` for numbered steps.

Why a virtual module: if the client imported each MDX file eagerly for its frontmatter and lazily for its body, Rollup would put every docs page into the main bundle. The plugin reads the YAML at build time instead, so only JSON reaches the client.

- [ ] **Step 1: Install dependencies**

```bash
pnpm add -D @mdx-js/rollup@^3.1.1 @mdx-js/mdx@^3.1.1 @types/mdx @types/mdast remark-gfm@^4.0.1 remark-frontmatter@^5.0.0 rehype-slug@^6.0.0 rehype-autolink-headings@^7.1.0 @shikijs/rehype@^4.5.0 shiki@^4.5.0 unist-util-visit@^5.1.0 mdast-util-to-string@^4.0.0 github-slugger@^2.0.0 estree-util-value-to-estree@^3.5.0 yaml
```

- [ ] **Step 2: Write the failing plugin tests**

`mdx/remark-export-toc.test.ts`:

```ts
import { createElement } from 'react'
import * as runtime from 'react/jsx-runtime'
import { renderToString } from 'react-dom/server'
import { evaluate } from '@mdx-js/mdx'
import rehypeSlug from 'rehype-slug'
import { describe, expect, it } from 'vitest'
import { remarkExportToc, type TocEntry } from './remark-export-toc'

const source = [
  '## Example',
  '',
  'Text.',
  '',
  '### Use `country` keys',
  '',
  '## Example',
  '',
  '#### Deep heading',
  '',
  '## Good to know',
].join('\n')

describe('remarkExportToc', () => {
  it('exports h2 and h3 entries whose ids match rehype-slug', async () => {
    const mod = await evaluate(source, {
      ...runtime,
      remarkPlugins: [remarkExportToc],
      rehypePlugins: [rehypeSlug],
    })
    const toc = mod.toc as TocEntry[]
    expect(toc).toEqual([
      { depth: 2, text: 'Example', id: 'example' },
      { depth: 3, text: 'Use country keys', id: 'use-country-keys' },
      { depth: 2, text: 'Example', id: 'example-1' },
      { depth: 2, text: 'Good to know', id: 'good-to-know' },
    ])
    const html = renderToString(createElement(mod.default))
    for (const entry of toc) expect(html).toContain(`id="${entry.id}"`)
  })

  it('exports an empty list when there are no headings', async () => {
    const mod = await evaluate('Just text.', { ...runtime, remarkPlugins: [remarkExportToc] })
    expect(mod.toc).toEqual([])
  })
})
```

`mdx/doc-frontmatter-plugin.test.ts`:

```ts
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { readDocFrontmatter } from './doc-frontmatter-plugin'

describe('readDocFrontmatter', () => {
  it('reads YAML frontmatter keyed by glob-style path', () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'docs-'))
    mkdirSync(path.join(dir, 'get-started'))
    writeFileSync(path.join(dir, 'index.mdx'), '---\ntitle: Docs\norder: 1\n---\n\nHello\n')
    writeFileSync(path.join(dir, 'get-started', 'install.mdx'), '---\ntitle: Install\nvideo:\n  number: 2\n  length: "3:30"\n---\n')
    writeFileSync(path.join(dir, 'get-started', 'notes.md'), '# ignored')
    writeFileSync(path.join(dir, 'bare.mdx'), 'No frontmatter')

    expect(readDocFrontmatter(dir)).toEqual({
      './docs/index.mdx': { title: 'Docs', order: 1 },
      './docs/get-started/install.mdx': { title: 'Install', video: { number: 2, length: '3:30' } },
      './docs/bare.mdx': null,
    })
  })
})
```

`src/test/fixtures/sample.mdx`:

````mdx
---
title: Sample
---

## First section

Some `inline code`.

```bash title="Start the stack"
docker compose -f docker-compose.demo.yml up -d
```

### Detail

| Key | Value |
|---|---|
| a | b |
````

`src/test/mdx-pipeline.test.tsx`:

```tsx
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import Sample, { toc } from './fixtures/sample.mdx'

describe('MDX pipeline', () => {
  const html = renderToString(<Sample />)

  it('strips frontmatter from the output', () => {
    expect(html).not.toContain('title: Sample')
  })

  it('exports a toc', () => {
    expect(toc).toEqual([
      { depth: 2, text: 'First section', id: 'first-section' },
      { depth: 3, text: 'Detail', id: 'detail' },
    ])
  })

  it('links headings and renders GFM tables', () => {
    expect(html).toContain('id="first-section"')
    expect(html).toContain('href="#first-section"')
    expect(html).toContain('<table>')
  })

  it('highlights code at build time and keeps the title', () => {
    expect(html).toMatch(/<pre[^>]*class="shiki/)
    expect(html).toContain('data-title="Start the stack"')
    expect(html).toContain('data-language="bash"')
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pnpm test mdx src/test/mdx-pipeline.test.tsx`
Expected: FAIL — plugin modules missing, `.mdx` import fails.

- [ ] **Step 4: Write `mdx/remark-export-toc.ts`**

```ts
import type { Root } from 'mdast'
import { valueToEstree } from 'estree-util-value-to-estree'
import GithubSlugger from 'github-slugger'
import { toString } from 'mdast-util-to-string'
import { visit } from 'unist-util-visit'

export type TocEntry = { depth: 2 | 3; text: string; id: string }

// Slugs every heading in document order (as rehype-slug does) so duplicate
// headings get the same "-1", "-2" suffixes, but exports only h2 and h3.
export function remarkExportToc() {
  return (tree: Root) => {
    const slugger = new GithubSlugger()
    const toc: TocEntry[] = []
    visit(tree, 'heading', (node) => {
      const text = toString(node)
      const id = slugger.slug(text)
      if (node.depth === 2 || node.depth === 3) toc.push({ depth: node.depth, text, id })
    })
    const esm = {
      type: 'mdxjsEsm',
      value: '',
      data: {
        estree: {
          type: 'Program',
          sourceType: 'module',
          body: [
            {
              type: 'ExportNamedDeclaration',
              specifiers: [],
              attributes: [],
              source: null,
              declaration: {
                type: 'VariableDeclaration',
                kind: 'const',
                declarations: [
                  {
                    type: 'VariableDeclarator',
                    id: { type: 'Identifier', name: 'toc' },
                    init: valueToEstree(toc),
                  },
                ],
              },
            },
          ],
        },
      },
    }
    tree.children.unshift(esm as unknown as Root['children'][number])
  }
}
```

- [ ] **Step 5: Write `mdx/doc-frontmatter-plugin.ts`**

```ts
import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import type { Plugin } from 'vite'
import { parse } from 'yaml'

const VIRTUAL_ID = 'virtual:doc-frontmatter'
const RESOLVED_ID = `\0${VIRTUAL_ID}`

export function readDocFrontmatter(docsDir: string): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  const files = (readdirSync(docsDir, { recursive: true }) as string[]).filter((file) => file.endsWith('.mdx')).sort()
  for (const file of files) {
    const text = readFileSync(path.join(docsDir, file), 'utf8')
    const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---/)
    result[`./docs/${file.split(path.sep).join('/')}`] = match ? parse(match[1]) : null
  }
  return result
}

export function docFrontmatterPlugin(docsDir: string): Plugin {
  return {
    name: 'fluxgate-doc-frontmatter',
    resolveId(id) {
      return id === VIRTUAL_ID ? RESOLVED_ID : undefined
    },
    load(id) {
      if (id !== RESOLVED_ID) return undefined
      this.addWatchFile(docsDir)
      return `export default ${JSON.stringify(readDocFrontmatter(docsDir))}`
    },
    configureServer(server) {
      server.watcher.on('all', (_event, file) => {
        if (!file.startsWith(docsDir) || !file.endsWith('.mdx')) return
        const mod = server.moduleGraph.getModuleById(RESOLVED_ID)
        if (mod) server.moduleGraph.invalidateModule(mod)
        server.ws.send({ type: 'full-reload' })
      })
    },
  }
}
```

`src/virtual.d.ts`:

```ts
declare module 'virtual:doc-frontmatter' {
  const frontmatter: Record<string, unknown>
  export default frontmatter
}
```

- [ ] **Step 6: Write `mdx/mdx-options.ts` and wire Vite**

```ts
import type { CompileOptions } from '@mdx-js/mdx'
import rehypeShiki from '@shikijs/rehype'
import rehypeAutolinkHeadings from 'rehype-autolink-headings'
import rehypeSlug from 'rehype-slug'
import remarkFrontmatter from 'remark-frontmatter'
import remarkGfm from 'remark-gfm'
import type { ShikiTransformer } from 'shiki'
import { remarkExportToc } from './remark-export-toc'

// Copies the code fence language and an optional title="..." meta onto <pre>.
const preAttributes: ShikiTransformer = {
  name: 'fluxgate-pre-attributes',
  pre(node) {
    node.properties['data-language'] = this.options.lang
    const raw = (this.options.meta as { __raw?: string } | undefined)?.__raw ?? ''
    const title = raw.match(/title="([^"]+)"/)?.[1]
    if (title) node.properties['data-title'] = title
  },
}

export const mdxOptions: CompileOptions = {
  remarkPlugins: [remarkGfm, remarkFrontmatter, remarkExportToc],
  rehypePlugins: [
    rehypeSlug,
    [rehypeAutolinkHeadings, { behavior: 'wrap' }],
    [rehypeShiki, { theme: 'github-dark-default', transformers: [preAttributes] }],
  ],
}
```

`vite.config.ts`:

```ts
import { fileURLToPath } from 'node:url'
import mdx from '@mdx-js/rollup'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { docFrontmatterPlugin } from './mdx/doc-frontmatter-plugin'
import { mdxOptions } from './mdx/mdx-options'

const docsDir = fileURLToPath(new URL('./src/content/docs', import.meta.url))

export default defineConfig({
  plugins: [
    { enforce: 'pre', ...mdx(mdxOptions) },
    react({ include: /\.(mdx|js|jsx|ts|tsx)$/ }),
    tailwindcss(),
    docFrontmatterPlugin(docsDir),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
```

Create the folder so the plugin has something to read: `mkdir -p src/content/docs` (the first page lands in Task 7).

- [ ] **Step 7: Write `src/styles/doc-prose.css` and import it**

Add `@import "./styles/doc-prose.css";` to `src/index.css` after the tokens import.

```css
.doc-prose {
  color: var(--foreground);
  font-size: 1rem;
  line-height: 1.75;
}
.doc-prose > * + * {
  margin-top: 1.1em;
}
.doc-prose h2 {
  margin-top: 2.4em;
  padding-top: 0.6em;
  border-top: 1px solid var(--border);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-bright);
  scroll-margin-top: 5rem;
}
.doc-prose h3 {
  margin-top: 1.8em;
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text-bright);
  scroll-margin-top: 5rem;
}
.doc-prose h2 > a,
.doc-prose h3 > a {
  color: inherit;
  text-decoration: none;
}
.doc-prose h2 > a:hover::after,
.doc-prose h3 > a:hover::after {
  content: " #";
  color: var(--text-dim);
}
.doc-prose a {
  color: var(--primary-text);
  font-weight: 500;
  text-underline-offset: 3px;
}
.doc-prose strong {
  font-weight: 600;
  color: var(--text-bright);
}
.doc-prose ul,
.doc-prose ol {
  padding-left: 1.4em;
}
.doc-prose ul {
  list-style: disc;
}
.doc-prose ol {
  list-style: decimal;
}
.doc-prose li + li {
  margin-top: 0.4em;
}
.doc-prose li::marker {
  color: var(--text-dim);
}
.doc-prose :not(pre) > code {
  padding: 0.12em 0.4em;
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  background: var(--bg-alt);
  font-family: var(--font-code);
  font-size: 0.875em;
  overflow-wrap: anywhere;
}
.doc-prose pre {
  margin: 0;
  overflow-x: auto;
  font-family: var(--font-code);
  font-size: 13px;
  line-height: 1.7;
}
.doc-prose table {
  display: block;
  width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.doc-prose th,
.doc-prose td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
.doc-prose th {
  font-weight: 600;
  color: var(--text-bright);
  background: var(--bg-alt);
}
.doc-prose blockquote {
  padding-left: 1rem;
  border-left: 3px solid var(--border-light);
  color: var(--muted-foreground);
}
.doc-prose img {
  max-width: 100%;
  height: auto;
  border: 1px solid var(--border);
  border-radius: 0.75rem;
}
.doc-prose hr {
  border: 0;
  border-top: 1px solid var(--border);
}

.doc-steps > ol {
  list-style: none;
  counter-reset: step;
  padding-left: 0;
}
.doc-steps > ol > li {
  position: relative;
  counter-increment: step;
  padding-left: 2.75rem;
  min-height: 2rem;
}
.doc-steps > ol > li::before {
  content: counter(step);
  position: absolute;
  left: 0;
  top: 0.1rem;
  display: inline-flex;
  width: 1.85rem;
  height: 1.85rem;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: var(--accent-dim);
  color: var(--primary-text);
  font-family: var(--font-code);
  font-size: 0.8rem;
  font-weight: 600;
}
.doc-steps > ol > li + li {
  margin-top: 1rem;
}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pnpm test`
Expected: PASS, including the fixture checks for `data-title="Start the stack"` and `class="shiki`.

If the `data-title` assertion fails, log `this.options.meta` inside the transformer once to see where `@shikijs/rehype` puts the raw meta string, adjust the lookup, and keep the test unchanged.

- [ ] **Step 9: Lint, build, commit**

Run: `pnpm lint && pnpm build` — expected success (no docs exist yet, so nothing new is prerendered).

```bash
git add -A
git commit -m "feat: add MDX pipeline with build-time highlighting and toc export

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Chapters, frontmatter schema, and docs registry

**Files:**
- Create: `src/content/chapters.ts`, `src/content/schema.ts`, `src/content/schema.test.ts`, `src/content/registry.ts`, `src/content/registry.test.ts`

**Interfaces:**
- Produces:
  - `CHAPTERS` (ordered), `type ChapterId`, `type Chapter = { id: ChapterId; title: string; number: number | null }`, `getChapter(id: ChapterId): Chapter`.
  - `type DocFrontmatter = { title: string; navTitle?: string; description: string; chapter: ChapterId; order: number; takeaway?: string; video?: { number: number; length: string }; prerequisites?: string[]; badge?: 'coming-soon' }`.
  - `parseFrontmatter(file: string, raw: unknown): DocFrontmatter` — throws `Error("<file>: <reason>")`.
  - `type DocEntry = { id: string; path: string; file: string; frontmatter: DocFrontmatter }`.
  - `pathFromFile(file: string): string`, `idFromFile(file: string): string`, `chapterFromFile(file: string): ChapterId`.
  - `buildDocRegistry(raw: Record<string, unknown>): DocEntry[]` — sorted by chapter order, then `order`.
  - `type DocNavGroup = { chapter: Chapter; docs: DocEntry[] }`, `getDocNav(entries: DocEntry[]): DocNavGroup[]`.
  - `getPrevNext(entries: DocEntry[], path: string): { prev?: DocEntry; next?: DocEntry }`.

- [ ] **Step 1: Write the failing tests**

`src/content/schema.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { parseFrontmatter } from './schema'

const valid = {
  title: 'Contexts',
  description: 'Declare the facts your rules use.',
  chapter: 'model-your-release',
  order: 2,
  takeaway: 'You declare country and user_tier.',
  video: { number: 5, length: '2:30' },
  prerequisites: ['environments-and-pipelines'],
}

describe('parseFrontmatter', () => {
  it('accepts a complete page', () => {
    expect(parseFrontmatter('a.mdx', valid)).toEqual(valid)
  })

  it('accepts optional navTitle and badge', () => {
    const fm = parseFrontmatter('a.mdx', { ...valid, navTitle: 'Contexts', badge: 'coming-soon' })
    expect(fm.navTitle).toBe('Contexts')
    expect(fm.badge).toBe('coming-soon')
  })

  it.each([
    [null, 'missing frontmatter'],
    [{ ...valid, title: '' }, '"title" must be a non-empty string'],
    [{ ...valid, description: 3 }, '"description" must be a non-empty string'],
    [{ ...valid, chapter: 'nope' }, 'unknown chapter "nope"'],
    [{ ...valid, order: 1.5 }, '"order" must be an integer'],
    [{ ...valid, video: { number: 17, length: '2:30' } }, '"video.number" must be an integer from 1 to 16'],
    [{ ...valid, video: { number: 5, length: '150s' } }, '"video.length" must look like 2:30'],
    [{ ...valid, prerequisites: 'contexts' }, '"prerequisites" must be a list of doc ids'],
    [{ ...valid, badge: 'beta' }, '"badge" must be "coming-soon"'],
    [{ ...valid, extra: true }, 'unknown key "extra"'],
  ])('rejects %j', (raw, message) => {
    expect(() => parseFrontmatter('docs/x.mdx', raw)).toThrow(`docs/x.mdx: ${message}`)
  })
})
```

`src/content/registry.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { buildDocRegistry, chapterFromFile, getDocNav, getPrevNext, idFromFile, pathFromFile } from './registry'

const fm = (chapter: string, order: number, extra: Record<string, unknown> = {}) => ({
  title: `T ${chapter} ${order}`,
  description: 'D',
  chapter,
  order,
  ...extra,
})

describe('file helpers', () => {
  it.each([
    ['./docs/index.mdx', '/docs/', 'overview', 'overview'],
    ['./docs/developer-guide.mdx', '/docs/developer-guide/', 'developer-guide', 'developer-guide'],
    ['./docs/get-started/install.mdx', '/docs/get-started/install/', 'install', 'get-started'],
    ['./docs/reference/edge-api.mdx', '/docs/reference/edge-api/', 'edge-api', 'reference'],
  ])('%s', (file, path, id, chapter) => {
    expect(pathFromFile(file)).toBe(path)
    expect(idFromFile(file)).toBe(id)
    expect(chapterFromFile(file)).toBe(chapter)
  })

  it('rejects a top-level page that is not index or developer-guide', () => {
    expect(() => chapterFromFile('./docs/stray.mdx')).toThrow('./docs/stray.mdx: top-level docs must be index.mdx or developer-guide.mdx')
  })

  it('rejects an unknown chapter folder', () => {
    expect(() => chapterFromFile('./docs/misc/a.mdx')).toThrow('./docs/misc/a.mdx: unknown chapter folder "misc"')
  })
})

describe('buildDocRegistry', () => {
  const raw = {
    './docs/model-your-release/contexts.mdx': fm('model-your-release', 2, { prerequisites: ['install'] }),
    './docs/get-started/install.mdx': fm('get-started', 2),
    './docs/index.mdx': fm('overview', 1),
    './docs/get-started/what-is-fluxgate.mdx': fm('get-started', 1),
  }

  it('sorts by chapter, then order', () => {
    expect(buildDocRegistry(raw).map((entry) => entry.path)).toEqual([
      '/docs/',
      '/docs/get-started/what-is-fluxgate/',
      '/docs/get-started/install/',
      '/docs/model-your-release/contexts/',
    ])
  })

  it('rejects frontmatter whose chapter disagrees with its folder', () => {
    expect(() => buildDocRegistry({ './docs/get-started/a.mdx': fm('reference', 1) })).toThrow(
      './docs/get-started/a.mdx: chapter "reference" does not match folder "get-started"',
    )
  })

  it('rejects duplicate ids', () => {
    expect(() =>
      buildDocRegistry({
        './docs/get-started/sso.mdx': fm('get-started', 1),
        './docs/integrations/sso.mdx': fm('integrations', 1),
      }),
    ).toThrow('duplicate doc id "sso"')
  })

  it('rejects duplicate order inside a chapter', () => {
    expect(() =>
      buildDocRegistry({
        './docs/get-started/a.mdx': fm('get-started', 1),
        './docs/get-started/b.mdx': fm('get-started', 1),
      }),
    ).toThrow('duplicate order 1 in chapter "get-started"')
  })

  it('rejects prerequisites that do not exist', () => {
    expect(() =>
      buildDocRegistry({ './docs/get-started/a.mdx': fm('get-started', 1, { prerequisites: ['ghost'] }) }),
    ).toThrow('./docs/get-started/a.mdx: prerequisite "ghost" is not a doc id')
  })
})

describe('navigation helpers', () => {
  const entries = buildDocRegistry({
    './docs/index.mdx': fm('overview', 1),
    './docs/get-started/what-is-fluxgate.mdx': fm('get-started', 1),
    './docs/get-started/install.mdx': fm('get-started', 2),
  })

  it('groups docs by chapter and skips empty chapters', () => {
    const nav = getDocNav(entries)
    expect(nav.map((group) => group.chapter.id)).toEqual(['overview', 'get-started'])
    expect(nav[1].docs).toHaveLength(2)
  })

  it('finds previous and next pages', () => {
    expect(getPrevNext(entries, '/docs/').prev).toBeUndefined()
    expect(getPrevNext(entries, '/docs/').next?.path).toBe('/docs/get-started/what-is-fluxgate/')
    expect(getPrevNext(entries, '/docs/get-started/install/').next).toBeUndefined()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test src/content`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write `src/content/chapters.ts`**

```ts
export const CHAPTERS = [
  { id: 'overview', title: 'Overview', number: null },
  { id: 'get-started', title: 'Get started', number: 1 },
  { id: 'model-your-release', title: 'Model your release', number: 2 },
  { id: 'connect-your-app', title: 'Connect your app', number: 3 },
  { id: 'ship-safely', title: 'Ship safely', number: 4 },
  { id: 'integrations', title: 'Integrations', number: 5 },
  { id: 'observe-and-operate', title: 'Observe and operate', number: 6 },
  { id: 'developer-guide', title: 'Developer guide', number: null },
  { id: 'reference', title: 'Reference', number: null },
] as const

export type ChapterId = (typeof CHAPTERS)[number]['id']
export type Chapter = { id: ChapterId; title: string; number: number | null }

export const CHAPTER_IDS: readonly string[] = CHAPTERS.map((chapter) => chapter.id)

export function isChapterId(value: unknown): value is ChapterId {
  return typeof value === 'string' && CHAPTER_IDS.includes(value)
}

export function getChapter(id: ChapterId): Chapter {
  const chapter = CHAPTERS.find((item) => item.id === id)
  if (!chapter) throw new Error(`unknown chapter "${id}"`)
  return chapter
}
```

- [ ] **Step 4: Write `src/content/schema.ts`**

```ts
import { isChapterId, type ChapterId } from './chapters'

export type DocFrontmatter = {
  title: string
  navTitle?: string
  description: string
  chapter: ChapterId
  order: number
  takeaway?: string
  video?: { number: number; length: string }
  prerequisites?: string[]
  badge?: 'coming-soon'
}

const KNOWN_KEYS = new Set(['title', 'navTitle', 'description', 'chapter', 'order', 'takeaway', 'video', 'prerequisites', 'badge'])

export function parseFrontmatter(file: string, raw: unknown): DocFrontmatter {
  const fail = (reason: string): never => {
    throw new Error(`${file}: ${reason}`)
  }
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return fail('missing frontmatter')
  const data = raw as Record<string, unknown>

  for (const key of Object.keys(data)) {
    if (!KNOWN_KEYS.has(key)) fail(`unknown key "${key}"`)
  }

  const text = (key: string, required: boolean): string | undefined => {
    const value = data[key]
    if (value === undefined && !required) return undefined
    if (typeof value !== 'string' || value.trim() === '') return fail(`"${key}" must be a non-empty string`)
    return value
  }

  const title = text('title', true) as string
  const description = text('description', true) as string
  const navTitle = text('navTitle', false)
  const takeaway = text('takeaway', false)

  const chapter = data.chapter
  if (!isChapterId(chapter)) return fail(`unknown chapter "${String(chapter)}"`)

  const order = data.order
  if (typeof order !== 'number' || !Number.isInteger(order)) return fail('"order" must be an integer')

  let video: DocFrontmatter['video']
  if (data.video !== undefined) {
    const raw = data.video as Record<string, unknown>
    const number = raw?.number
    const length = raw?.length
    if (typeof number !== 'number' || !Number.isInteger(number) || number < 1 || number > 16) {
      return fail('"video.number" must be an integer from 1 to 16')
    }
    if (typeof length !== 'string' || !/^\d{1,2}:\d{2}$/.test(length)) return fail('"video.length" must look like 2:30')
    video = { number, length }
  }

  let prerequisites: string[] | undefined
  if (data.prerequisites !== undefined) {
    const list = data.prerequisites
    if (!Array.isArray(list) || !list.every((item) => typeof item === 'string')) {
      return fail('"prerequisites" must be a list of doc ids')
    }
    prerequisites = list
  }

  let badge: DocFrontmatter['badge']
  if (data.badge !== undefined) {
    if (data.badge !== 'coming-soon') return fail('"badge" must be "coming-soon"')
    badge = 'coming-soon'
  }

  const result: DocFrontmatter = { title, description, chapter, order }
  if (navTitle) result.navTitle = navTitle
  if (takeaway) result.takeaway = takeaway
  if (video) result.video = video
  if (prerequisites) result.prerequisites = prerequisites
  if (badge) result.badge = badge
  return result
}
```

- [ ] **Step 5: Write `src/content/registry.ts`**

```ts
import { CHAPTERS, getChapter, isChapterId, type Chapter, type ChapterId } from './chapters'
import { parseFrontmatter, type DocFrontmatter } from './schema'

export type DocEntry = { id: string; path: string; file: string; frontmatter: DocFrontmatter }
export type DocNavGroup = { chapter: Chapter; docs: DocEntry[] }

function relative(file: string): string {
  return file.replace(/^\.\/docs\//, '').replace(/\.mdx$/, '')
}

export function pathFromFile(file: string): string {
  const rel = relative(file)
  return rel === 'index' ? '/docs/' : `/docs/${rel}/`
}

export function idFromFile(file: string): string {
  const rel = relative(file)
  return rel === 'index' ? 'overview' : rel.split('/').at(-1)!
}

export function chapterFromFile(file: string): ChapterId {
  const parts = relative(file).split('/')
  if (parts.length === 1) {
    if (parts[0] === 'index') return 'overview'
    if (parts[0] === 'developer-guide') return 'developer-guide'
    throw new Error(`${file}: top-level docs must be index.mdx or developer-guide.mdx`)
  }
  const folder = parts[0]
  if (!isChapterId(folder) || folder === 'overview' || folder === 'developer-guide') {
    throw new Error(`${file}: unknown chapter folder "${folder}"`)
  }
  return folder
}

const chapterIndex = (id: ChapterId) => CHAPTERS.findIndex((chapter) => chapter.id === id)

export function buildDocRegistry(raw: Record<string, unknown>): DocEntry[] {
  const entries = Object.entries(raw).map(([file, data]) => {
    const frontmatter = parseFrontmatter(file, data)
    const folderChapter = chapterFromFile(file)
    if (frontmatter.chapter !== folderChapter) {
      throw new Error(`${file}: chapter "${frontmatter.chapter}" does not match folder "${folderChapter}"`)
    }
    return { id: idFromFile(file), path: pathFromFile(file), file, frontmatter }
  })

  const ids = new Map<string, string>()
  const orders = new Set<string>()
  for (const entry of entries) {
    const other = ids.get(entry.id)
    if (other) throw new Error(`duplicate doc id "${entry.id}" in ${other} and ${entry.file}`)
    ids.set(entry.id, entry.file)
    const orderKey = `${entry.frontmatter.chapter}:${entry.frontmatter.order}`
    if (orders.has(orderKey)) {
      throw new Error(`duplicate order ${entry.frontmatter.order} in chapter "${entry.frontmatter.chapter}"`)
    }
    orders.add(orderKey)
  }
  for (const entry of entries) {
    for (const prerequisite of entry.frontmatter.prerequisites ?? []) {
      if (!ids.has(prerequisite)) throw new Error(`${entry.file}: prerequisite "${prerequisite}" is not a doc id`)
    }
  }

  return entries.sort(
    (a, b) =>
      chapterIndex(a.frontmatter.chapter) - chapterIndex(b.frontmatter.chapter) || a.frontmatter.order - b.frontmatter.order,
  )
}

export function getDocNav(entries: DocEntry[]): DocNavGroup[] {
  return CHAPTERS.map((chapter) => ({
    chapter: getChapter(chapter.id),
    docs: entries.filter((entry) => entry.frontmatter.chapter === chapter.id),
  })).filter((group) => group.docs.length > 0)
}

export function getPrevNext(entries: DocEntry[], path: string): { prev?: DocEntry; next?: DocEntry } {
  const index = entries.findIndex((entry) => entry.path === path)
  if (index === -1) return {}
  return { prev: entries[index - 1], next: entries[index + 1] }
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pnpm test src/content`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add docs chapters, frontmatter schema, and registry

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Route registry, doc rendering, prerender, and dist check

**Files:**
- Create: `src/content/doc-module.ts`, `src/content/docs-index.ts`, `src/content/videos.ts`, `src/content/videos.test.ts`, `src/routes.ts`, `src/routes.test.ts`, `src/site.test.ts`, `src/docs/DocPage.tsx` (minimal, replaced in Task 9), `src/content/docs/index.mdx`, `scripts/lib/doc-paths.mjs`, `scripts/lib/doc-paths.test.mjs`, `scripts/check-dist.mjs`
- Modify: `src/site.ts`, `src/App.tsx`, `src/entry-server.tsx`, `src/main.tsx`, `scripts/prerender.mjs`, `package.json`

**Interfaces:**
- Consumes: `buildDocRegistry`, `DocEntry` (Task 6); `virtual:doc-frontmatter`, `TocEntry` (Task 5); `normalizePath` (Task 3).
- Produces:
  - `type DocModule = { default: ComponentType<{ components?: MDXComponents }>; toc: TocEntry[] }` in `@/content/doc-module`.
  - `docEntries: DocEntry[]`, `docLoaders: Record<string, () => Promise<DocModule>>` in `@/content/docs-index`.
  - `type VideoInfo = { title: string; youtubeId: string; uploadDate: string }`, `videos: Record<number, VideoInfo>`, `getVideo(n: number): VideoInfo | undefined`, `lengthToIsoDuration(length: string): string`, `youtubeIdFromUrl(url: string): string | null` in `@/content/videos`.
  - `PRODUCT_PATHS`, `type ProductPath`, `type Route = { kind: 'product'; path: ProductPath } | { kind: 'doc'; path: string; entry: DocEntry }`, `routes: Route[]`, `findRoute(path: string): Route | undefined` in `@/routes`.
  - `getRouteMeta(path: string): RouteMeta` (now covers docs) in `@/site`.
  - `App({ path: string; docModule?: DocModule })`.
  - `render(path: string): Promise<string>` in `entry-server.tsx`.
  - `pathFromDocFile(relativeToDocsDir: string): string` in `scripts/lib/doc-paths.mjs`.

- [ ] **Step 1: Write the failing tests**

`src/content/videos.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { getVideo, lengthToIsoDuration, videos, youtubeIdFromUrl } from './videos'

describe('videos', () => {
  it('lists all 16 videos', () => {
    expect(Object.keys(videos).map(Number)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
    expect(getVideo(7)?.title).toBe('Targeting rules')
    expect(getVideo(99)).toBeUndefined()
  })

  it('converts a length to an ISO 8601 duration', () => {
    expect(lengthToIsoDuration('4:00')).toBe('PT4M0S')
    expect(lengthToIsoDuration('2:30')).toBe('PT2M30S')
  })

  it.each([
    ['https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s', 'dQw4w9WgXcQ'],
    ['https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
    ['https://example.com/video', null],
  ])('youtubeIdFromUrl(%s)', (url, id) => {
    expect(youtubeIdFromUrl(url)).toBe(id)
  })
})
```

`src/routes.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { findRoute, routes } from './routes'

describe('findRoute', () => {
  it('finds product pages', () => {
    expect(findRoute('/')?.kind).toBe('product')
    expect(findRoute('/performance')?.path).toBe('/performance/')
  })

  it('finds the docs landing with or without slash or index.html', () => {
    for (const path of ['/docs', '/docs/', '/docs/index.html']) {
      const route = findRoute(path)
      expect(route?.kind).toBe('doc')
      expect(route?.path).toBe('/docs/')
    }
  })

  it('returns undefined for unknown paths', () => {
    expect(findRoute('/nope/')).toBeUndefined()
  })

  it('has unique paths', () => {
    const paths = routes.map((route) => route.path)
    expect(new Set(paths).size).toBe(paths.length)
  })
})
```

`src/site.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { getRouteMeta } from './site'

describe('getRouteMeta', () => {
  it('keeps product meta', () => {
    expect(getRouteMeta('/').title).toBe('FluxGate | Feature flag delivery platform')
  })

  it('builds doc meta from frontmatter', () => {
    const meta = getRouteMeta('/docs/')
    expect(meta.path).toBe('/docs/')
    expect(meta.title).toMatch(/\| FluxGate docs$/)
    const types = meta.jsonLd.map((schema) => schema['@type'])
    expect(types).toContain('TechArticle')
    expect(types).toContain('BreadcrumbList')
  })
})
```

`scripts/lib/doc-paths.test.mjs`:

```js
import { describe, expect, it } from 'vitest'
import { pathFromDocFile } from './doc-paths.mjs'
import { pathFromFile } from '../../src/content/registry'

describe('pathFromDocFile', () => {
  it.each(['index.mdx', 'developer-guide.mdx', 'get-started/install.mdx', 'reference/edge-api.mdx'])(
    'agrees with the app registry for %s',
    (file) => {
      expect(pathFromDocFile(file)).toBe(pathFromFile(`./docs/${file}`))
    },
  )
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test src/content/videos.test.ts src/routes.test.ts src/site.test.ts scripts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write the content wiring**

`src/content/doc-module.ts`:

```ts
import type { ComponentType } from 'react'
import type { MDXComponents } from 'mdx/types'

// Same shape as TocEntry in mdx/remark-export-toc.ts (that file belongs to the node tsconfig).
export type TocEntry = { depth: 2 | 3; text: string; id: string }

export type DocModule = {
  default: ComponentType<{ components?: MDXComponents }>
  toc: TocEntry[]
}
```

`src/content/docs-index.ts`:

```ts
import frontmatter from 'virtual:doc-frontmatter'
import type { DocModule } from './doc-module'
import { buildDocRegistry } from './registry'

export const docEntries = buildDocRegistry(frontmatter)

// Lazy: each docs page becomes its own chunk.
export const docLoaders = import.meta.glob<DocModule>('./docs/**/*.mdx')
```

`src/content/videos.ts` (YouTube ids are filled in Task 24):

```ts
export type VideoInfo = { title: string; youtubeId: string; uploadDate: string }

export const videos: Record<number, VideoInfo> = {
  1: { title: 'What is FluxGate', youtubeId: '', uploadDate: '' },
  2: { title: 'Install and first boot', youtubeId: '', uploadDate: '' },
  3: { title: 'Teams, users and roles', youtubeId: '', uploadDate: '' },
  4: { title: 'Environments and pipelines', youtubeId: '', uploadDate: '' },
  5: { title: 'Contexts', youtubeId: '', uploadDate: '' },
  6: { title: 'Create your first feature', youtubeId: '', uploadDate: '' },
  7: { title: 'Targeting rules', youtubeId: '', uploadDate: '' },
  8: { title: 'Clients and edge server', youtubeId: '', uploadDate: '' },
  9: { title: 'Automation and CI', youtubeId: '', uploadDate: '' },
  10: { title: 'Approvals and policies', youtubeId: '', uploadDate: '' },
  11: { title: 'Safety nets', youtubeId: '', uploadDate: '' },
  12: { title: 'Jira setup', youtubeId: '', uploadDate: '' },
  13: { title: 'Jira end to end', youtubeId: '', uploadDate: '' },
  14: { title: 'Jev AI assistance', youtubeId: '', uploadDate: '' },
  15: { title: 'Dashboards', youtubeId: '', uploadDate: '' },
  16: { title: 'Going to production', youtubeId: '', uploadDate: '' },
}

export function getVideo(number: number): VideoInfo | undefined {
  return videos[number]
}

export function lengthToIsoDuration(length: string): string {
  const [minutes, seconds] = length.split(':').map(Number)
  return `PT${minutes}M${seconds}S`
}

export function youtubeIdFromUrl(url: string): string | null {
  const match = url.match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([\w-]{11})/)
  return match ? match[1] : null
}
```

`src/routes.ts`:

```ts
import { docEntries } from './content/docs-index'
import type { DocEntry } from './content/registry'
import { normalizePath } from './lib/paths'

export const PRODUCT_PATHS = ['/', '/architecture/', '/performance/', '/comparison/'] as const
export type ProductPath = (typeof PRODUCT_PATHS)[number]

export type Route = { kind: 'product'; path: ProductPath } | { kind: 'doc'; path: string; entry: DocEntry }

export const routes: Route[] = [
  ...PRODUCT_PATHS.map((path): Route => ({ kind: 'product', path })),
  ...docEntries.map((entry): Route => ({ kind: 'doc', path: entry.path, entry })),
]

export function findRoute(path: string): Route | undefined {
  const normalized = normalizePath(path)
  return routes.find((route) => route.path === normalized)
}
```

- [ ] **Step 4: Rework `src/site.ts`**

1. Delete `export type RoutePath` and change `RouteMeta.path` to `path: string`.
2. Rename `export const routes: RouteMeta[] = [...]` to `const productMetaList: RouteMeta[] = [...]` (entries unchanged).
3. Replace `getRouteMeta` with the version below and add the doc meta builder. Final additions to `site.ts`:

```ts
import { getChapter } from './content/chapters'
import type { DocEntry } from './content/registry'
import { getVideo, lengthToIsoDuration } from './content/videos'
import { normalizePath } from './lib/paths'
import { findRoute } from './routes'

const DEFAULT_DOC_IMAGE = `${SITE_URL}/images/system-overview.jpg`

function docMeta(entry: DocEntry): RouteMeta {
  const { frontmatter } = entry
  const url = `${SITE_URL}${entry.path}`
  const chapter = getChapter(frontmatter.chapter)
  const jsonLd: Array<Record<string, unknown>> = [
    organizationSchema,
    {
      '@context': 'https://schema.org',
      '@type': 'TechArticle',
      headline: frontmatter.title,
      description: frontmatter.description,
      url,
      image: DEFAULT_DOC_IMAGE,
      about: ['Feature flags', 'FluxGate'],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Docs', item: `${SITE_URL}/docs/` },
        { '@type': 'ListItem', position: 2, name: chapter.title, item: `${SITE_URL}/docs/#${chapter.id}` },
        { '@type': 'ListItem', position: 3, name: frontmatter.title, item: url },
      ],
    },
  ]
  const video = frontmatter.video ? getVideo(frontmatter.video.number) : undefined
  if (frontmatter.video && video?.youtubeId) {
    jsonLd.push({
      '@context': 'https://schema.org',
      '@type': 'VideoObject',
      name: `${frontmatter.title} | FluxGate`,
      description: frontmatter.description,
      thumbnailUrl: `https://i.ytimg.com/vi/${video.youtubeId}/hqdefault.jpg`,
      uploadDate: video.uploadDate,
      duration: lengthToIsoDuration(frontmatter.video.length),
      embedUrl: `https://www.youtube-nocookie.com/embed/${video.youtubeId}`,
    })
  }
  return {
    path: entry.path,
    title: `${frontmatter.title} | FluxGate docs`,
    description: frontmatter.description,
    image: DEFAULT_DOC_IMAGE,
    priority: entry.path === '/docs/' ? '0.9' : '0.7',
    changefreq: 'monthly',
    jsonLd,
  }
}

export function getRouteMeta(path: string): RouteMeta {
  const route = findRoute(path)
  if (route?.kind === 'doc') return docMeta(route.entry)
  const normalized = normalizePath(path)
  return productMetaList.find((meta) => meta.path === normalized) ?? productMetaList[0]
}
```

`site.ts` and `routes.ts` import each other only through functions called at render time, but to stay safe, `routes.ts` must not import from `site.ts`.

- [ ] **Step 5: Minimal `DocPage` and the docs landing seed**

`src/docs/DocPage.tsx` (Task 9 replaces it):

```tsx
import type { DocModule } from '@/content/doc-module'
import type { DocEntry } from '@/content/registry'

export function DocPage({ entry, module }: { entry: DocEntry; module: DocModule }) {
  const Content = module.default
  return (
    <div className="mx-auto w-full max-w-[760px] px-4 py-10 sm:px-6">
      <article data-pagefind-body className="doc-prose">
        <h1 className="text-4xl font-semibold text-text-bright">{entry.frontmatter.title}</h1>
        <Content />
      </article>
    </div>
  )
}
```

`src/content/docs/index.mdx` (Task 12 writes the full landing):

```mdx
---
title: FluxGate documentation
navTitle: Introduction
description: Learn FluxGate step by step, from install to production, with a video and a written guide for every topic.
chapter: overview
order: 1
---

FluxGate separates deploying code from releasing a feature. These docs follow one story from install to production: the Checkout team at Juniper Market rolls out express checkout safely.

## Start here

Install FluxGate with Docker Compose in the developer guide, then follow the chapters in order. Each chapter has a short video and a written guide with examples.
```

- [ ] **Step 6: Render docs in `App`, server, and client**

`src/App.tsx` — new signature and route switch (keep the shell markup from Task 3):

```tsx
import type { DocModule } from './content/doc-module'
import { DocPage } from './docs/DocPage'
import { normalizePath } from './lib/paths'
import { findRoute, type Route } from './routes'
// ...existing imports of SiteHeader, SiteFooter, pages

function renderRoute(route: Route | undefined, docModule: DocModule | undefined) {
  if (!route) return <NotFoundPage />
  if (route.kind === 'doc') return docModule ? <DocPage entry={route.entry} module={docModule} /> : <NotFoundPage />
  switch (route.path) {
    case '/':
      return <HomePage />
    case '/architecture/':
      return <ArchitecturePage />
    case '/performance/':
      return <PerformancePage />
    case '/comparison/':
      return <ComparisonPage />
  }
}

function App({ path, docModule }: { path: string; docModule?: DocModule }) {
  const route = findRoute(path)
  const currentPath = route?.path ?? normalizePath(path)
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* skip link from Task 3 */}
      <SiteHeader path={currentPath} />
      <main id="main" className="flex-1">
        {renderRoute(route, docModule)}
      </main>
      <SiteFooter />
    </div>
  )
}

export default App
```

`src/entry-server.tsx`:

```tsx
import { StrictMode } from 'react'
import { renderToString } from 'react-dom/server'
import App from './App'
import { docLoaders } from './content/docs-index'
import { findRoute } from './routes'

export async function render(path: string): Promise<string> {
  const route = findRoute(path)
  const docModule = route?.kind === 'doc' ? await docLoaders[route.entry.file]() : undefined
  return renderToString(
    <StrictMode>
      <App path={path} docModule={docModule} />
    </StrictMode>,
  )
}

export { getRouteMeta } from './site'
export { routes } from './routes'
```

`src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { hydrateRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { docLoaders } from './content/docs-index'
import { findRoute } from './routes'

const path = window.location.pathname
const route = findRoute(path)
// Load the page's MDX chunk before hydrating so the markup matches the prerendered HTML.
const docModule = route?.kind === 'doc' ? await docLoaders[route.entry.file]() : undefined

hydrateRoot(
  document.getElementById('root')!,
  <StrictMode>
    <App path={path} docModule={docModule} />
  </StrictMode>,
)
```

- [ ] **Step 7: Update `scripts/prerender.mjs`**

1. In `metaTags`, make JSON-LD safe inside `<script>`: `JSON.stringify(schema).replaceAll('<', '\\u003c')`.
2. Make `renderRoute` async and await the render:

```js
async function renderRoute(route) {
  const meta = getRouteMeta(route.path)
  const canonical = `https://flux.forgeopslabs.com${meta.path}`
  const body = await render(route.path)
  return template
    .replace(/<title>.*?<\/title>/, `<title>${escapeHtml(meta.title)}</title>`)
    .replace(/<meta name="description" content=".*?" \/>/, `<meta name="description" content="${escapeHtml(meta.description)}" />`)
    .replace(/<link rel="canonical" href=".*?" \/>/, `<link rel="canonical" href="${canonical}" />`)
    .replace('    <!--seo-tags-->', metaTags(meta))
    .replace('<div id="root"></div>', () => `<div id="root">${body}</div>`)
}
```

(The replacer function stops `$` sequences in page content from being read as replacement patterns.)

3. In the loop: `await writeFile(output, await renderRoute(route), 'utf8')`.

The sitemap loop already reads `routes`; it now includes every docs page.

- [ ] **Step 8: Write `scripts/lib/doc-paths.mjs` and `scripts/check-dist.mjs`**

`scripts/lib/doc-paths.mjs`:

```js
// Mirrors pathFromFile in src/content/registry.ts (a parity test keeps them equal).
export function pathFromDocFile(relativeToDocsDir) {
  const rel = relativeToDocsDir.split('\\').join('/').replace(/\.mdx$/, '')
  return rel === 'index' ? '/docs/' : `/docs/${rel}/`
}
```

`scripts/check-dist.mjs`:

```js
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { pathFromDocFile } from './lib/doc-paths.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const dist = path.join(root, 'dist')
const docsDir = path.join(root, 'src/content/docs')
const errors = []

const sitemap = readFileSync(path.join(dist, 'sitemap.xml'), 'utf8')
const locs = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map((match) => match[1])
const sitemapPaths = new Set(locs.map((loc) => new URL(loc).pathname))

for (const loc of locs) {
  const pathname = new URL(loc).pathname
  const file = pathname === '/' ? path.join(dist, 'index.html') : path.join(dist, pathname, 'index.html')
  if (!existsSync(file)) {
    errors.push(`${pathname}: missing ${path.relative(root, file)}`)
    continue
  }
  const html = readFileSync(file, 'utf8')
  if (!/<title>[^<]+<\/title>/.test(html)) errors.push(`${pathname}: missing <title>`)
  if (!html.includes(`<link rel="canonical" href="${loc}" />`)) errors.push(`${pathname}: wrong canonical`)
  if (!html.includes('application/ld+json')) errors.push(`${pathname}: missing JSON-LD`)
  if (pathname.startsWith('/docs/')) {
    const article = html.match(/<article[^>]*data-pagefind-body[^>]*>([\s\S]*?)<\/article>/)
    const text = article ? article[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() : ''
    if (text.length < 200) errors.push(`${pathname}: prerendered article is empty or too short (${text.length} chars)`)
  }
}

for (const file of readdirSync(docsDir, { recursive: true })) {
  if (!String(file).endsWith('.mdx')) continue
  const docPath = pathFromDocFile(String(file))
  if (!sitemapPaths.has(docPath)) errors.push(`${docPath}: docs page missing from sitemap`)
}

if (errors.length > 0) {
  console.error(`check-dist: ${errors.length} problem(s)\n${errors.map((error) => `  - ${error}`).join('\n')}`)
  process.exit(1)
}
console.log(`check-dist: ${locs.length} pages OK`)
```

`package.json` `build` script becomes:

```json
"build": "tsc -b && vite build && vite build --ssr src/entry-server.tsx --outDir dist-ssr && node scripts/prerender.mjs && node scripts/check-dist.mjs"
```

- [ ] **Step 9: Run tests and build**

Run: `pnpm test && pnpm lint && pnpm build`
Expected: tests PASS; build ends with `check-dist: 5 pages OK`; `dist/docs/index.html` contains the landing text inside `<article data-pagefind-body`.

- [ ] **Step 10: Confirm the client bundle stays small**

Run:

```bash
entry=$(grep -o 'assets/[^"]*\.js' dist/index.html | head -1)
echo "entry: $entry"
grep -l "Start here" dist/assets/*.js
```

Expected: exactly one file contains "Start here", and it is not the entry file printed first. Both files may be named `index-<hash>.js` (one for `index.html`, one for `index.mdx`); compare the hashes.

- [ ] **Step 11: Confirm hydration works**

`pnpm preview`, open `http://localhost:4173/docs/` in the built-in browser, read console messages. Expected: no hydration warning; theme toggle works on the docs page.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat: route registry with prerendered docs pages and dist check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: MDX components

**Files:**
- Create: `src/components/mdx/VideoEmbed.tsx`, `Steps.tsx`, `Callout.tsx`, `CodeBlock.tsx`, `CodeTabs.tsx`, `UiLabel.tsx`, `RoleBadge.tsx`, `index.ts`, `src/components/mdx/mdx.test.tsx`

**Interfaces:**
- Consumes: `TerminalBlock`, `Badge`, `cn`.
- Produces:
  - `VideoEmbed({ youtubeId: string; title: string })` — placeholder when `youtubeId` is empty; thumbnail button, then the `youtube-nocookie` iframe after click.
  - `Steps({ children })`, `Callout({ type?: 'note'|'tip'|'warn'; title?: string; children })`, `CodeBlock` (MDX `pre` override), `CodeTabs({ labels: string[]; children })`, `UiLabel({ children })`, `RoleBadge({ role: 'admin'|'team-admin'|'requester'|'approver' })`.
  - `mdxComponents: MDXComponents` — `{ pre: CodeBlock, Steps, Callout, CodeTabs, UiLabel, RoleBadge }`.

- [ ] **Step 1: Write the failing tests**

`src/components/mdx/mdx.test.tsx`:

```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { Callout } from './Callout'
import { CodeBlock } from './CodeBlock'
import { CodeTabs } from './CodeTabs'
import { RoleBadge } from './RoleBadge'
import { VideoEmbed } from './VideoEmbed'

describe('VideoEmbed', () => {
  it('shows a placeholder and no iframe when the id is empty', () => {
    const { container } = render(<VideoEmbed youtubeId="" title="Contexts" />)
    expect(screen.getByText('Video coming soon')).toBeTruthy()
    expect(container.querySelector('iframe')).toBeNull()
  })

  it('loads the privacy-enhanced iframe only after a click', () => {
    const { container } = render(<VideoEmbed youtubeId="dQw4w9WgXcQ" title="Contexts" />)
    expect(container.querySelector('iframe')).toBeNull()
    expect(container.querySelector('img')?.getAttribute('src')).toBe('https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg')
    fireEvent.click(screen.getByRole('button', { name: 'Play video: Contexts' }))
    const iframe = container.querySelector('iframe')
    expect(iframe?.getAttribute('src')).toBe('https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1&rel=0')
    expect(iframe?.getAttribute('title')).toBe('Contexts video')
  })
})

describe('Callout', () => {
  it('labels the note with its title or type', () => {
    render(<Callout type="warn">Careful</Callout>)
    expect(screen.getByRole('note', { name: 'Warning' })).toBeTruthy()
    render(<Callout title="Use a stable key">Body</Callout>)
    expect(screen.getByRole('note', { name: 'Use a stable key' })).toBeTruthy()
  })
})

describe('CodeBlock', () => {
  it('wraps highlighted code in the terminal chrome with its title and drops the Shiki background', () => {
    const html = renderToString(
      <CodeBlock data-title="Start the stack" data-language="bash" className="shiki" style={{ backgroundColor: '#0d1117' }}>
        <code>docker compose up -d</code>
      </CodeBlock>,
    )
    expect(html).toContain('data-slot="terminal-block"')
    expect(html).toContain('Start the stack')
    expect(html).not.toContain('background-color')
  })

  it('falls back to the language as title', () => {
    const html = renderToString(
      <CodeBlock data-language="json">
        <code>{'{}'}</code>
      </CodeBlock>,
    )
    expect(html).toContain('>json<')
  })
})

describe('CodeTabs', () => {
  it('renders one tab per label and keeps every pane in the HTML', () => {
    const html = renderToString(
      <CodeTabs labels={['curl', 'JavaScript']}>
        <pre>curl one</pre>
        <pre>js two</pre>
      </CodeTabs>,
    )
    expect(html).toContain('curl one')
    expect(html).toContain('js two')
    expect(html.match(/role="tab"/g)).toHaveLength(2)
  })

  it('throws when labels and panes disagree', () => {
    expect(() =>
      renderToString(
        <CodeTabs labels={['a', 'b']}>
          <pre>only one</pre>
        </CodeTabs>,
      ),
    ).toThrow('CodeTabs: 2 labels for 1 code blocks')
  })
})

describe('RoleBadge', () => {
  it('maps role ids to FluxGate role names', () => {
    render(<RoleBadge role="team-admin" />)
    expect(screen.getByText('Team Admin')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test src/components/mdx`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write the components**

`src/components/mdx/VideoEmbed.tsx`:

```tsx
import { useState } from 'react'
import { Play } from 'lucide-react'

export function VideoEmbed({ youtubeId, title }: { youtubeId: string; title: string }) {
  const [playing, setPlaying] = useState(false)

  if (!youtubeId) {
    return (
      <div
        data-pagefind-ignore
        className="my-6 flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border-light bg-bg-alt p-6 text-center"
      >
        <Play className="h-8 w-8 text-text-dim" aria-hidden="true" />
        <p className="font-semibold text-text-bright">Video coming soon</p>
        <p className="text-sm text-muted-foreground">{title}</p>
      </div>
    )
  }

  if (playing) {
    return (
      <div data-pagefind-ignore className="my-6 aspect-video w-full overflow-hidden rounded-xl border border-border bg-black">
        <iframe
          className="h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${youtubeId}?autoplay=1&rel=0`}
          title={`${title} video`}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
        />
      </div>
    )
  }

  return (
    <button
      type="button"
      data-pagefind-ignore
      onClick={() => setPlaying(true)}
      aria-label={`Play video: ${title}`}
      className="group relative my-6 block aspect-video w-full overflow-hidden rounded-xl border border-border bg-black focus-visible:focus-ring"
    >
      <img src={`https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`} alt="" loading="lazy" className="h-full w-full object-cover opacity-90 transition-opacity group-hover:opacity-100" />
      <span className="absolute inset-0 m-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-card-hover">
        <Play className="h-7 w-7" aria-hidden="true" />
      </span>
    </button>
  )
}
```

`src/components/mdx/Steps.tsx`:

```tsx
import type { ReactNode } from 'react'

export function Steps({ children }: { children: ReactNode }) {
  return <div className="doc-steps">{children}</div>
}
```

`src/components/mdx/Callout.tsx`:

```tsx
import type { ReactNode } from 'react'
import { Info, Lightbulb, TriangleAlert, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

const variants: Record<'note' | 'tip' | 'warn', { label: string; icon: LucideIcon; box: string; iconClass: string }> = {
  note: { label: 'Note', icon: Info, box: 'border-info/30 bg-info/10', iconClass: 'text-info' },
  tip: { label: 'Tip', icon: Lightbulb, box: 'border-primary/30 bg-accent-dim', iconClass: 'text-primary-text' },
  warn: { label: 'Warning', icon: TriangleAlert, box: 'border-warning/30 bg-warning/10', iconClass: 'text-warning' },
}

export function Callout({ type = 'note', title, children }: { type?: 'note' | 'tip' | 'warn'; title?: string; children: ReactNode }) {
  const variant = variants[type]
  const Icon = variant.icon
  return (
    <aside role="note" aria-label={title ?? variant.label} className={cn('my-6 flex gap-3 rounded-lg border p-4 text-[0.95rem]', variant.box)}>
      <Icon className={cn('mt-1 h-5 w-5 shrink-0', variant.iconClass)} aria-hidden="true" />
      <div className="min-w-0 [&>*+*]:mt-2 [&>p]:m-0">
        {title && <p className="font-semibold text-text-bright">{title}</p>}
        {children}
      </div>
    </aside>
  )
}
```

`src/components/mdx/CodeBlock.tsx`:

```tsx
import type { ComponentProps } from 'react'
import { TerminalBlock } from '@/components/ui/terminal-block'
import { cn } from '@/lib/utils'

type CodeBlockProps = ComponentProps<'pre'> & { 'data-title'?: string; 'data-language'?: string }

export function CodeBlock({ 'data-title': title, 'data-language': language, className, ...rest }: CodeBlockProps) {
  return (
    <TerminalBlock title={title ?? language}>
      {/* Shiki's inline background is dropped so the terminal background shows. */}
      <pre {...rest} style={undefined} className={cn('overflow-x-auto p-4 font-mono text-[13px] leading-relaxed', className)} />
    </TerminalBlock>
  )
}
```

`src/components/mdx/CodeTabs.tsx`:

```tsx
import { Children, isValidElement, type ReactNode } from 'react'
import * as Tabs from '@radix-ui/react-tabs'

export function CodeTabs({ labels, children }: { labels: string[]; children: ReactNode }) {
  const panes = Children.toArray(children).filter(isValidElement)
  if (panes.length !== labels.length) {
    throw new Error(`CodeTabs: ${labels.length} labels for ${panes.length} code blocks`)
  }
  return (
    <Tabs.Root defaultValue="0" className="my-6">
      <Tabs.List aria-label="Code examples" className="flex gap-1 overflow-x-auto border-b border-border">
        {labels.map((label, index) => (
          <Tabs.Trigger
            key={label}
            value={String(index)}
            className="-mb-px border-b-2 border-transparent px-3 py-2 font-mono text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:focus-ring data-[state=active]:border-primary data-[state=active]:text-text-bright"
          >
            {label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {panes.map((pane, index) => (
        // forceMount keeps every pane in the prerendered HTML for search and SEO.
        <Tabs.Content key={labels[index]} value={String(index)} forceMount className="data-[state=inactive]:hidden [&>[data-slot=terminal-block]]:mt-3">
          {pane}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  )
}
```

`src/components/mdx/UiLabel.tsx`:

```tsx
import type { ReactNode } from 'react'

export function UiLabel({ children }: { children: ReactNode }) {
  return <span className="rounded border border-border bg-bg-alt px-1.5 py-0.5 text-[0.9em] font-semibold text-text-bright">{children}</span>
}
```

`src/components/mdx/RoleBadge.tsx`:

```tsx
import { Badge } from '@/components/ui/badge'

const roles = {
  admin: { label: 'System admin', variant: 'error' },
  'team-admin': { label: 'Team Admin', variant: 'warning' },
  requester: { label: 'Requester', variant: 'info' },
  approver: { label: 'Approver', variant: 'success' },
} as const

export function RoleBadge({ role }: { role: keyof typeof roles }) {
  const { label, variant } = roles[role]
  return (
    <Badge variant={variant} className="align-middle">
      {label}
    </Badge>
  )
}
```

`src/components/mdx/index.ts`:

```ts
import type { MDXComponents } from 'mdx/types'
import { Callout } from './Callout'
import { CodeBlock } from './CodeBlock'
import { CodeTabs } from './CodeTabs'
import { RoleBadge } from './RoleBadge'
import { Steps } from './Steps'
import { UiLabel } from './UiLabel'

export const mdxComponents: MDXComponents = {
  pre: CodeBlock,
  Steps,
  Callout,
  CodeTabs,
  UiLabel,
  RoleBadge,
}

export { VideoEmbed } from './VideoEmbed'
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm test src/components/mdx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add MDX components for docs pages

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Docs layout

**Files:**
- Create: `src/docs/DocsSidebar.tsx`, `src/docs/DocsMobileNav.tsx`, `src/docs/DocToc.tsx`, `src/docs/DocHeader.tsx`, `src/docs/DocPager.tsx`, `src/docs/DocPage.test.tsx`
- Modify: `src/docs/DocPage.tsx` (full version)

**Interfaces:**
- Consumes: `DocEntry`, `DocNavGroup`, `getDocNav`, `getPrevNext` (Task 6); `docEntries` (Task 7); `DocModule`, `TocEntry`; `getVideo` (Task 7); `mdxComponents`, `VideoEmbed` (Task 8); `getChapter`; `Badge`, `Eyebrow`.
- Produces: `DocPage({ entry: DocEntry; module: DocModule; entries?: DocEntry[] })`; `DocsSidebar({ nav: DocNavGroup[]; currentPath: string })`; `DocsMobileNav({ nav; currentPath })`; `DocToc({ toc: TocEntry[] })`; `DocHeader({ entry: DocEntry; entries: DocEntry[] })`; `DocPager({ prev?: DocEntry; next?: DocEntry })`.

- [ ] **Step 1: Write the failing test**

`src/docs/DocPage.test.tsx`:

```tsx
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DocModule } from '@/content/doc-module'
import { buildDocRegistry } from '@/content/registry'
import { DocPage } from './DocPage'

const entries = buildDocRegistry({
  './docs/index.mdx': { title: 'FluxGate documentation', navTitle: 'Introduction', description: 'D', chapter: 'overview', order: 1 },
  './docs/model-your-release/environments-and-pipelines.mdx': { title: 'Environments and pipelines', description: 'D', chapter: 'model-your-release', order: 1 },
  './docs/model-your-release/contexts.mdx': {
    title: 'Contexts',
    description: 'D',
    chapter: 'model-your-release',
    order: 2,
    takeaway: 'You declare the facts a rule can use.',
    video: { number: 5, length: '2:30' },
    prerequisites: ['environments-and-pipelines'],
  },
})

const module: DocModule = {
  default: () => (
    <>
      <h2 id="what-a-context-is">What a context is</h2>
      <p>Body text.</p>
    </>
  ),
  toc: [{ depth: 2, text: 'What a context is', id: 'what-a-context-is' }],
}

describe('DocPage', () => {
  const contexts = entries[2]

  it('renders header, takeaway, video placeholder, body, toc, and pager', () => {
    render(<DocPage entry={contexts} module={module} entries={entries} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Contexts' })).toBeTruthy()
    expect(screen.getByText('You declare the facts a rule can use.')).toBeTruthy()
    expect(screen.getByText('2:30 video')).toBeTruthy()
    expect(screen.getByText('Video coming soon')).toBeTruthy()
    expect(screen.getByText('Body text.')).toBeTruthy()

    const toc = screen.getByRole('navigation', { name: 'On this page' })
    expect(within(toc).getByRole('link', { name: 'What a context is' }).getAttribute('href')).toBe('#what-a-context-is')

    expect(screen.getAllByRole('link', { name: 'Environments and pipelines' }).length).toBeGreaterThan(0)

    const pager = screen.getByRole('navigation', { name: 'Previous and next' })
    expect(within(pager).getByText('Environments and pipelines')).toBeTruthy()
  })

  it('marks the current page in the sidebar', () => {
    render(<DocPage entry={contexts} module={module} entries={entries} />)
    const sidebar = screen.getAllByRole('navigation', { name: 'Documentation' })[0]
    expect(within(sidebar).getByRole('link', { name: 'Contexts' }).getAttribute('aria-current')).toBe('page')
    expect(within(sidebar).getByRole('link', { name: 'Introduction' })).toBeTruthy()
  })

  it('wraps the indexable content in data-pagefind-body', () => {
    const { container } = render(<DocPage entry={contexts} module={module} entries={entries} />)
    const article = container.querySelector('article[data-pagefind-body]')
    expect(article?.textContent).toContain('Body text.')
    expect(article?.querySelector('h1')?.textContent).toBe('Contexts')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm test src/docs`
Expected: FAIL — the minimal `DocPage` has no toc, sidebar, or pager.

- [ ] **Step 3: Write the layout pieces**

`src/docs/DocsSidebar.tsx`:

```tsx
import type { DocNavGroup } from '@/content/registry'
import { cn } from '@/lib/utils'

export function DocsSidebar({ nav, currentPath }: { nav: DocNavGroup[]; currentPath: string }) {
  return (
    <nav aria-label="Documentation" className="flex flex-col gap-6 text-sm">
      {nav.map((group) => (
        <div key={group.chapter.id} id={`nav-${group.chapter.id}`}>
          <p className="mb-2 px-3 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-text-dim">
            {group.chapter.number ? `${group.chapter.number} · ` : ''}
            {group.chapter.title}
          </p>
          <ul className="flex flex-col gap-0.5">
            {group.docs.map((doc) => {
              const active = doc.path === currentPath
              return (
                <li key={doc.path}>
                  <a
                    href={doc.path}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'flex min-h-9 items-center rounded-md px-3 py-1.5 font-medium no-underline transition-colors focus-visible:focus-ring',
                      active ? 'bg-accent-dim text-text-bright' : 'text-muted-foreground hover:bg-card-hover hover:text-foreground',
                    )}
                  >
                    {doc.frontmatter.navTitle ?? doc.frontmatter.title}
                  </a>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}
```

`src/docs/DocsMobileNav.tsx`:

```tsx
import * as Dialog from '@radix-ui/react-dialog'
import { PanelLeft, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { DocNavGroup } from '@/content/registry'
import { DocsSidebar } from './DocsSidebar'

export function DocsMobileNav({ nav, currentPath }: { nav: DocNavGroup[]; currentPath: string }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <Button variant="secondary" size="sm" className="mb-6 lg:hidden">
          <PanelLeft aria-hidden="true" />
          Docs menu
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-overlay" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-[min(320px,85vw)] overflow-y-auto border-r border-border bg-card p-4 shadow-card-hover">
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-sm font-semibold text-text-bright">Documentation</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close docs menu">
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">All documentation pages by chapter</Dialog.Description>
          <DocsSidebar nav={nav} currentPath={currentPath} />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
```

`src/docs/DocToc.tsx`:

```tsx
import type { TocEntry } from '@/content/doc-module'
import { cn } from '@/lib/utils'

export function DocToc({ toc }: { toc: TocEntry[] }) {
  if (toc.length === 0) return null
  return (
    <nav aria-label="On this page" className="text-sm">
      <p className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-text-dim">On this page</p>
      <ul className="flex flex-col gap-2 border-l border-border">
        {toc.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className={cn('-ml-px block border-l border-transparent pl-3 text-muted-foreground no-underline hover:border-primary hover:text-foreground', item.depth === 3 && 'pl-6')}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
```

`src/docs/DocHeader.tsx`:

```tsx
import { Clock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Eyebrow } from '@/components/ui/eyebrow'
import { getChapter } from '@/content/chapters'
import type { DocEntry } from '@/content/registry'

export function DocHeader({ entry, entries }: { entry: DocEntry; entries: DocEntry[] }) {
  const { frontmatter } = entry
  const chapter = getChapter(frontmatter.chapter)
  const prerequisites = (frontmatter.prerequisites ?? [])
    .map((id) => entries.find((candidate) => candidate.id === id))
    .filter((candidate): candidate is DocEntry => Boolean(candidate))

  return (
    <header className="mb-6">
      <nav aria-label="Breadcrumb" className="mb-4 text-sm text-text-dim">
        <a href="/docs/" className="no-underline hover:text-foreground">Docs</a>
        <span aria-hidden="true"> / </span>
        <span>{chapter.title}</span>
      </nav>
      <Eyebrow className="mb-2 text-primary-text">
        {chapter.number ? `Chapter ${chapter.number} · ` : ''}
        {chapter.title}
      </Eyebrow>
      <h1 className="text-3xl font-semibold tracking-[-0.02em] text-text-bright sm:text-4xl">{frontmatter.title}</h1>
      {frontmatter.takeaway && <p className="mt-4 text-lg text-muted-foreground">{frontmatter.takeaway}</p>}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {frontmatter.video && (
          <Badge variant="secondary">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {`${frontmatter.video.length} video`}
          </Badge>
        )}
        {frontmatter.badge === 'coming-soon' && <Badge variant="warning">Coming soon</Badge>}
        {prerequisites.length > 0 && (
          <span className="flex flex-wrap items-center gap-2 text-sm text-text-dim">
            Builds on:
            {prerequisites.map((doc) => (
              <a key={doc.id} href={doc.path} className="rounded-full border border-border px-2.5 py-0.5 text-xs font-medium text-muted-foreground no-underline hover:border-primary hover:text-foreground">
                {doc.frontmatter.title}
              </a>
            ))}
          </span>
        )}
      </div>
    </header>
  )
}
```

`src/docs/DocPager.tsx`:

```tsx
import { ArrowLeft, ArrowRight } from 'lucide-react'
import type { DocEntry } from '@/content/registry'

export function DocPager({ prev, next }: { prev?: DocEntry; next?: DocEntry }) {
  if (!prev && !next) return null
  return (
    <nav aria-label="Previous and next" data-pagefind-ignore className="mt-16 grid gap-4 border-t border-border pt-8 sm:grid-cols-2">
      {prev ? (
        <a href={prev.path} className="flex flex-col gap-1 rounded-lg border border-border p-4 no-underline transition-colors hover:border-primary">
          <span className="inline-flex items-center gap-1 text-xs text-text-dim"><ArrowLeft className="h-3 w-3" aria-hidden="true" />Previous</span>
          <span className="font-semibold text-text-bright">{prev.frontmatter.title}</span>
        </a>
      ) : (
        <span />
      )}
      {next && (
        <a href={next.path} className="flex flex-col items-end gap-1 rounded-lg border border-border p-4 text-right no-underline transition-colors hover:border-primary">
          <span className="inline-flex items-center gap-1 text-xs text-text-dim">Next<ArrowRight className="h-3 w-3" aria-hidden="true" /></span>
          <span className="font-semibold text-text-bright">{next.frontmatter.title}</span>
        </a>
      )}
    </nav>
  )
}
```

`src/docs/DocPage.tsx` (full):

```tsx
import { mdxComponents, VideoEmbed } from '@/components/mdx'
import type { DocModule } from '@/content/doc-module'
import { docEntries } from '@/content/docs-index'
import { getDocNav, getPrevNext, type DocEntry } from '@/content/registry'
import { getVideo } from '@/content/videos'
import { DocHeader } from './DocHeader'
import { DocPager } from './DocPager'
import { DocsMobileNav } from './DocsMobileNav'
import { DocsSidebar } from './DocsSidebar'
import { DocToc } from './DocToc'

export function DocPage({ entry, module, entries = docEntries }: { entry: DocEntry; module: DocModule; entries?: DocEntry[] }) {
  const Content = module.default
  const nav = getDocNav(entries)
  const { prev, next } = getPrevNext(entries, entry.path)
  const video = entry.frontmatter.video ? getVideo(entry.frontmatter.video.number) : undefined

  return (
    <div className="mx-auto grid w-full max-w-[1400px] gap-10 px-4 sm:px-6 lg:grid-cols-[248px_minmax(0,1fr)] xl:grid-cols-[248px_minmax(0,1fr)_200px]">
      <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] overflow-y-auto py-8 pr-2 lg:block">
        <DocsSidebar nav={nav} currentPath={entry.path} />
      </aside>
      <div className="min-w-0 py-8">
        <DocsMobileNav nav={nav} currentPath={entry.path} />
        <article data-pagefind-body className="mx-auto max-w-[760px]">
          <DocHeader entry={entry} entries={entries} />
          {entry.frontmatter.video && <VideoEmbed youtubeId={video?.youtubeId ?? ''} title={entry.frontmatter.title} />}
          <div className="doc-prose">
            <Content components={mdxComponents} />
          </div>
        </article>
        <div className="mx-auto max-w-[760px]">
          <DocPager prev={prev} next={next} />
        </div>
      </div>
      <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] overflow-y-auto py-8 xl:block">
        <DocToc toc={module.toc} />
      </aside>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm test`
Expected: PASS (all suites).

- [ ] **Step 5: Build and check in the browser**

Run: `pnpm build && pnpm preview`. Open `/docs/` in the built-in browser at 1440 px and 375 px, light and dark. Check: sidebar visible on desktop, "Docs menu" drawer on mobile, no horizontal scroll, no console hydration warning.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: docs layout with sidebar, toc, header, and pager

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Search

**Files:**
- Create: `src/components/search/pagefind.ts`, `src/components/search/SearchDialog.tsx`, `src/components/search/SearchDialog.test.tsx`
- Modify: `src/App.tsx` (pass `searchSlot={<SearchDialog />}` to `SiteHeader`), `package.json` (pagefind dev dependency, build script), `scripts/check-dist.mjs`

**Interfaces:**
- Produces:
  - `type PagefindResultData = { url: string; excerpt: string; meta: { title?: string } }`, `type Pagefind = { search: (query: string) => Promise<{ results: Array<{ id: string; data: () => Promise<PagefindResultData> }> }> }`, `loadPagefind(): Promise<Pagefind>` in `@/components/search/pagefind`.
  - `SearchDialog({ load?: () => Promise<Pagefind> })` — trigger button in the header, opens on click, `⌘K` / `Ctrl+K`, or `/` (when focus is not in a text field).

- [ ] **Step 1: Install Pagefind**

```bash
pnpm add -D pagefind@^1.5.2
```

- [ ] **Step 2: Write the failing tests**

`src/components/search/SearchDialog.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Pagefind } from './pagefind'
import { SearchDialog } from './SearchDialog'

const fakePagefind = (titles: string[]): Pagefind => ({
  search: vi.fn(async () => ({
    results: titles.map((title, index) => ({
      id: String(index),
      data: async () => ({ url: `/docs/x${index}/`, excerpt: `about <mark>${title}</mark>`, meta: { title } }),
    })),
  })),
})

function open() {
  fireEvent.click(screen.getByRole('button', { name: /Search docs/ }))
}

describe('SearchDialog', () => {
  it('opens with the keyboard shortcut', async () => {
    render(<SearchDialog load={async () => fakePagefind([])} />)
    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    expect(await screen.findByRole('dialog')).toBeTruthy()
  })

  it('shows results with highlighted excerpts', async () => {
    render(<SearchDialog load={async () => fakePagefind(['Targeting rules'])} />)
    open()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'targeting' } })
    const link = await screen.findByRole('link', { name: /Targeting rules/ })
    expect(link.getAttribute('href')).toBe('/docs/x0/')
    expect(link.querySelector('mark')?.textContent).toBe('Targeting rules')
  })

  it('says when nothing matches', async () => {
    render(<SearchDialog load={async () => fakePagefind([])} />)
    open()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'zzz' } })
    expect(await screen.findByText('No results for “zzz”.')).toBeTruthy()
  })

  it('explains when the index cannot load', async () => {
    render(<SearchDialog load={async () => Promise.reject(new Error('404'))} />)
    open()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'install' } })
    await waitFor(() => expect(screen.getByText('Search is available on the built site only.')).toBeTruthy())
  })

  it('does not search for an empty query', async () => {
    const pagefind = fakePagefind(['x'])
    render(<SearchDialog load={async () => pagefind} />)
    open()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: '   ' } })
    await new Promise((resolve) => setTimeout(resolve, 250))
    expect(pagefind.search).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pnpm test src/components/search`
Expected: FAIL — modules not found.

- [ ] **Step 4: Write the Pagefind loader**

`src/components/search/pagefind.ts`:

```ts
export type PagefindResultData = { url: string; excerpt: string; meta: { title?: string } }

export type Pagefind = {
  search: (query: string) => Promise<{ results: Array<{ id: string; data: () => Promise<PagefindResultData> }> }>
}

const PAGEFIND_URL = '/pagefind/pagefind.js'

let cached: Promise<Pagefind> | undefined

// The index exists only in the production build (pagefind runs after prerender).
export function loadPagefind(): Promise<Pagefind> {
  cached ??= import(/* @vite-ignore */ PAGEFIND_URL).catch((error: unknown) => {
    cached = undefined
    throw error
  }) as Promise<Pagefind>
  return cached
}
```

- [ ] **Step 5: Write `SearchDialog`**

`src/components/search/SearchDialog.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { loadPagefind, type Pagefind, type PagefindResultData } from './pagefind'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; query: string; results: PagefindResultData[] }
  | { status: 'unavailable' }

function isTypingTarget(target: EventTarget | null) {
  return target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
}

export function SearchDialog({ load = loadPagefind }: { load?: () => Promise<Pagefind> }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [state, setState] = useState<State>({ status: 'idle' })
  const request = useRef(0)
  const loadRef = useRef(load)

  useEffect(() => {
    loadRef.current = load
  })

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const shortcut = (event.key === 'k' && (event.metaKey || event.ctrlKey)) || (event.key === '/' && !isTypingTarget(event.target))
      if (shortcut) {
        event.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    const trimmed = query.trim()
    if (!trimmed) {
      setState({ status: 'idle' })
      return
    }
    const id = ++request.current
    setState({ status: 'loading' })
    const timer = window.setTimeout(async () => {
      try {
        const pagefind = await loadRef.current()
        const search = await pagefind.search(trimmed)
        const results = await Promise.all(search.results.slice(0, 8).map((result) => result.data()))
        if (id === request.current) setState({ status: 'done', query: trimmed, results })
      } catch {
        if (id === request.current) setState({ status: 'unavailable' })
      }
    }, 150)
    return () => window.clearTimeout(timer)
  }, [query])

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="secondary" size="sm" className="h-9 gap-2 px-3 text-muted-foreground" aria-label="Search docs">
          <Search aria-hidden="true" />
          <span className="hidden md:inline">Search docs</span>
          <Kbd className="hidden md:inline-flex">⌘K</Kbd>
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-overlay" />
        <Dialog.Content className="fixed left-1/2 top-[10vh] z-50 w-[min(640px,calc(100vw-2rem))] -translate-x-1/2 overflow-hidden rounded-xl border border-border bg-card shadow-card-hover">
          <Dialog.Title className="sr-only">Search the documentation</Dialog.Title>
          <Dialog.Description className="sr-only">Type to search all FluxGate docs pages.</Dialog.Description>
          <div className="flex items-center gap-2 border-b border-border px-4">
            <Search className="h-4 w-4 text-text-dim" aria-hidden="true" />
            <input
              type="search"
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search docs, for example “OFREP” or “encryption key”"
              className="h-12 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-text-dim"
            />
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close search">
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </div>
          <div className="max-h-[60vh] overflow-y-auto p-2" aria-live="polite">
            {state.status === 'loading' && <p className="p-4 text-sm text-text-dim">Searching…</p>}
            {state.status === 'unavailable' && <p className="p-4 text-sm text-text-dim">Search is available on the built site only.</p>}
            {state.status === 'done' && state.results.length === 0 && (
              <p className="p-4 text-sm text-text-dim">{`No results for “${state.query}”.`}</p>
            )}
            {state.status === 'done' && state.results.length > 0 && (
              <ul className="flex flex-col gap-1">
                {state.results.map((result) => (
                  <li key={result.url}>
                    <a href={result.url} className="block rounded-md p-3 no-underline hover:bg-card-hover focus-visible:focus-ring">
                      <span className="block text-sm font-semibold text-text-bright">{result.meta.title ?? result.url}</span>
                      {/* Pagefind escapes page text and adds only <mark> tags. */}
                      <span className="mt-1 block text-sm text-muted-foreground [&_mark]:bg-accent-dim [&_mark]:text-text-bright" dangerouslySetInnerHTML={{ __html: result.excerpt }} />
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
```

In `src/App.tsx`: `<SiteHeader path={currentPath} searchSlot={<SearchDialog />} />`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pnpm test src/components/search`
Expected: PASS.

- [ ] **Step 7: Index the build and check it**

`package.json` `build` script:

```json
"build": "tsc -b && vite build && vite build --ssr src/entry-server.tsx --outDir dist-ssr && node scripts/prerender.mjs && pagefind --site dist && node scripts/check-dist.mjs"
```

Append to `scripts/check-dist.mjs`, before the error report:

```js
if (!existsSync(path.join(dist, 'pagefind', 'pagefind.js'))) errors.push('search: dist/pagefind/pagefind.js missing (did pagefind run?)')
```

- [ ] **Step 8: Build and try search**

Run: `pnpm build && pnpm preview`. In the built-in browser press `⌘K`, type "start". Expected: the docs landing appears as a result; the excerpt highlights the match. Run `pnpm dev`, open search, type a word: "Search is available on the built site only."

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: static docs search with Pagefind

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Content lint and downloadable files

**Files:**
- Create: `scripts/lib/lint-docs.mjs`, `scripts/lib/lint-docs.test.mjs`, `scripts/check-docs.mjs`, `scripts/sync-downloads.mjs`, `public/downloads/docker-compose.demo.yml`, `public/downloads/config.demo.toml`
- Modify: `package.json`

**Interfaces:**
- Consumes: `pathFromDocFile` (Task 7).
- Produces: `lintDoc(file: string, text: string, knownPaths: Set<string>, publicFiles: Set<string>): string[]` in `scripts/lib/lint-docs.mjs`; scripts `pnpm check:docs` and `pnpm sync:downloads`.

Rules `lintDoc` enforces (each message starts with `<file>:<line>: `):

| Rule | Pattern | Message |
|---|---|---|
| Private source path with line | `/\b[\w./-]+\.(rs\|tsx\|ts\|jsx):\d+/` | `private source reference "<match>"` |
| Private repository or folder name | `/\b(feature-toggle-backend\|feature-toggle-ui\|feature-toggle-shared\|evaluation-engine\|feature-edge-server\|fluxgate\.wiki\|fluxgate-cli)\b/` | `private source reference "<match>"` |
| CLI command | `/^\s*(\$\s*)?fluxgate\s+[a-z]/` on a line | `the fluxgate CLI is not public` |
| Image tag | `/keaz\/flux-gate-(backend\|edge\|ui):([\w.-]+)/g` with tag not `v1.2.0` and not `latest` | `image tag "<tag>" must be v1.2.0 or latest` |
| Internal link | `](/...)` or `href="/..."`, hash and query removed | `broken link "<path>"` unless the path is in `knownPaths`, or `/downloads/<x>` / `/images/<x>` exists in `publicFiles` |
| Unreplaced draft marker | `/\b(TODO\|TBD\|FIXME)\b/` | `draft marker "<match>"` |

- [ ] **Step 1: Write the failing tests**

`scripts/lib/lint-docs.test.mjs`:

```js
import { describe, expect, it } from 'vitest'
import { lintDoc } from './lint-docs.mjs'

const known = new Set(['/', '/docs/', '/docs/get-started/install/'])
const publicFiles = new Set(['/downloads/docker-compose.demo.yml', '/images/ui/features-list-light.jpg'])
const lint = (text) => lintDoc('a.mdx', text, known, publicFiles)

describe('lintDoc', () => {
  it('passes clean content', () => {
    expect(
      lint(
        [
          'Run `docker compose -f docker-compose.demo.yml up -d`.',
          'Image `keaz/flux-gate-backend:v1.2.0` or `keaz/flux-gate-ui:latest`.',
          'See [install](/docs/get-started/install/#prerequisites) and [the file](/downloads/docker-compose.demo.yml).',
          '<img src="/images/ui/features-list-light.jpg" />',
          'Visit [GitHub](https://github.com/forgeopslabs).',
        ].join('\n'),
      ),
    ).toEqual([])
  })

  it('flags private source references', () => {
    expect(lint('see FeatureCreate.tsx:1138')).toEqual(['a.mdx:1: private source reference "FeatureCreate.tsx:1138"'])
    expect(lint('\nin feature-toggle-backend')).toEqual(['a.mdx:2: private source reference "feature-toggle-backend"'])
  })

  it('flags CLI commands', () => {
    expect(lint('```bash\nfluxgate feature list\n```')).toEqual(['a.mdx:2: the fluxgate CLI is not public'])
  })

  it('flags wrong image tags', () => {
    expect(lint('keaz/flux-gate-edge:v1.1.0')).toEqual(['a.mdx:1: image tag "v1.1.0" must be v1.2.0 or latest'])
  })

  it('flags broken internal links', () => {
    expect(lint('[x](/docs/nope/)')).toEqual(['a.mdx:1: broken link "/docs/nope/"'])
    expect(lint('<a href="/downloads/missing.toml">x</a>')).toEqual(['a.mdx:1: broken link "/downloads/missing.toml"'])
  })

  it('flags draft markers', () => {
    expect(lint('TODO: write this')).toEqual(['a.mdx:1: draft marker "TODO"'])
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test scripts/lib/lint-docs.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `scripts/lib/lint-docs.mjs`**

```js
const PRIVATE_PATH = /\b[\w./-]+\.(?:rs|tsx|ts|jsx):\d+/g
const PRIVATE_NAME = /\b(?:feature-toggle-backend|feature-toggle-ui|feature-toggle-shared|evaluation-engine|feature-edge-server|fluxgate\.wiki|fluxgate-cli)\b/g
const CLI = /^\s*(?:\$\s*)?fluxgate\s+[a-z]/
const IMAGE = /keaz\/flux-gate-(?:backend|edge|ui):([\w.-]+)/g
const LINK = /\]\((\/[^)\s]*)\)|href="(\/[^"]*)"|src="(\/[^"]*)"/g
const DRAFT = /\b(?:TODO|TBD|FIXME)\b/g
const ALLOWED_TAGS = new Set(['v1.2.0', 'latest'])

export function lintDoc(file, text, knownPaths, publicFiles) {
  const errors = []
  text.split('\n').forEach((line, index) => {
    const at = `${file}:${index + 1}: `
    for (const match of line.matchAll(PRIVATE_PATH)) errors.push(`${at}private source reference "${match[0]}"`)
    for (const match of line.matchAll(PRIVATE_NAME)) errors.push(`${at}private source reference "${match[0]}"`)
    if (CLI.test(line)) errors.push(`${at}the fluxgate CLI is not public`)
    for (const match of line.matchAll(IMAGE)) {
      if (!ALLOWED_TAGS.has(match[1])) errors.push(`${at}image tag "${match[1]}" must be v1.2.0 or latest`)
    }
    for (const match of line.matchAll(LINK)) {
      const target = (match[1] ?? match[2] ?? match[3]).split(/[?#]/)[0]
      const isPublicFile = target.startsWith('/downloads/') || target.startsWith('/images/')
      const ok = isPublicFile ? publicFiles.has(target) : knownPaths.has(target)
      if (!ok) errors.push(`${at}broken link "${target}"`)
    }
    for (const match of line.matchAll(DRAFT)) errors.push(`${at}draft marker "${match[0]}"`)
  })
  return errors
}
```

- [ ] **Step 4: Write `scripts/check-docs.mjs`**

```js
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { pathFromDocFile } from './lib/doc-paths.mjs'
import { lintDoc } from './lib/lint-docs.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const docsDir = path.join(root, 'src/content/docs')
const publicDir = path.join(root, 'public')

const docFiles = readdirSync(docsDir, { recursive: true }).map(String).filter((file) => file.endsWith('.mdx'))
const knownPaths = new Set(['/', '/architecture/', '/performance/', '/comparison/', ...docFiles.map(pathFromDocFile)])
const publicFiles = new Set(
  readdirSync(publicDir, { recursive: true })
    .map(String)
    .filter((file) => statSync(path.join(publicDir, file)).isFile())
    .map((file) => `/${file.split(path.sep).join('/')}`),
)

const errors = docFiles.flatMap((file) =>
  lintDoc(`src/content/docs/${file}`, readFileSync(path.join(docsDir, file), 'utf8'), knownPaths, publicFiles),
)

if (errors.length > 0) {
  console.error(`check-docs: ${errors.length} problem(s)\n${errors.map((error) => `  - ${error}`).join('\n')}`)
  process.exit(1)
}
console.log(`check-docs: ${docFiles.length} pages OK`)
```

- [ ] **Step 5: Write `scripts/sync-downloads.mjs` and sync once**

```js
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = path.resolve(root, '../docs/demo-videos/assets')
const target = path.join(root, 'public/downloads')
const files = ['docker-compose.demo.yml', 'config.demo.toml']

if (!existsSync(source)) {
  console.error(`sync-downloads: ${source} not found. Run this from the FeatureToggle monorepo checkout.`)
  process.exit(1)
}
mkdirSync(target, { recursive: true })
for (const file of files) {
  copyFileSync(path.join(source, file), path.join(target, file))
  console.log(`sync-downloads: copied ${file}`)
}
```

`package.json` scripts: add `"check:docs": "node scripts/check-docs.mjs"`, `"sync:downloads": "node scripts/sync-downloads.mjs"`, and make `build` start with `node scripts/check-docs.mjs && `.

Run: `pnpm sync:downloads`
Expected: both files copied into `public/downloads/`.

- [ ] **Step 6: Run tests and build**

Run: `pnpm test && pnpm build`
Expected: PASS; build prints `check-docs: 1 pages OK` first and `check-dist: ... OK` last; `dist/downloads/docker-compose.demo.yml` exists.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: docs content lint and downloadable demo stack files

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Phase 2 is complete: the docs engine works end to end with one landing page.

---
# Phase 3 — Content foundation

Content tasks write prose, not code, so their "test" is the build gate: `pnpm check:docs` (content lint), `pnpm build` (registry validation, prerender, `check-dist`), plus a factual check against the demo scripts and, where a page shows commands or responses, against a running v1.2.0 stack. Every content task follows `docs/AUTHORING.md`, which Task 12 creates.

### Task 12: Authoring guide, page scaffold, docs landing, and the exemplar page

**Files:**
- Create: `docs/AUTHORING.md`, every docs page in the table below (scaffold), `src/content/docs/model-your-release/contexts.mdx` (complete exemplar)
- Modify: `src/content/docs/index.mdx` (full landing)

**Interfaces:**
- Consumes: frontmatter schema (Task 6), MDX components (Task 8), lint rules (Task 11).
- Produces: all 22 docs routes exist, so later tasks can link anywhere without breaking the link lint; `docs/AUTHORING.md` is the rulebook for Tasks 13–21.

Why scaffold everything first: the link lint fails on links to pages that do not exist yet, and `prerequisites` must resolve. Creating every page now (with real, short content) lets each later task link forward freely.

#### Page table (frontmatter values are exact)

| File under `src/content/docs/` | title | navTitle | order | video (number, length) | prerequisites | description |
|---|---|---|---|---|---|---|
| `index.mdx` | FluxGate documentation | Introduction | 1 | — | — | Learn FluxGate step by step, from install to production, with a video and a written guide for every topic. |
| `get-started/what-is-fluxgate.mdx` | What is FluxGate | — | 1 | 1, 2:00 | — | FluxGate separates deploying code from releasing a feature. Meet the backend, edge server, admin UI, and SDKs that make that work. |
| `get-started/install.mdx` | Install and first boot | Install | 2 | 2, 3:30 | what-is-fluxgate | Run the full FluxGate stack locally with Docker Compose and create the first admin in under five minutes. |
| `get-started/teams-users-roles.mdx` | Teams, users and roles | — | 3 | 3, 3:30 | install | Create a team, add a requester and an approver, and learn what the three system roles allow. |
| `model-your-release/environments-and-pipelines.mdx` | Environments and pipelines | — | 1 | 4, 3:30 | teams-users-roles | Model Development, Staging and Production, chain them into a release pipeline, and add an approval policy. |
| `model-your-release/contexts.mdx` | Contexts | — | 2 | 5, 2:30 | environments-and-pipelines | Declare the facts your targeting rules use, such as country and user tier, and send them from your app at evaluation time. |
| `model-your-release/first-feature.mdx` | Create your first feature | First feature | 3 | 6, 4:00 | contexts | Create a feature flag with an owner, a ticket, two variants and a release pipeline, then read the feature list and detail page. |
| `model-your-release/targeting-rules.mdx` | Targeting rules | — | 4 | 7, 4:00 | first-feature | Serve a variant to one segment first, then split everyone else by percentage, and understand why rule order matters. |
| `connect-your-app/clients-and-edge-server.mdx` | Clients and edge server | — | 1 | 8, 4:00 | targeting-rules | Create clients, start the edge server, and evaluate flags with curl, OFREP, or the OpenFeature SDK. |
| `connect-your-app/automation-and-ci.mdx` | Automation and CI | — | 2 | 9, 3:30 | clients-and-edge-server | Let a CI job check a flag with its own scoped token and one REST call, and fail the build when the flag is off. |
| `ship-safely/approvals-and-policies.mdx` | Approvals and policies | — | 1 | 10, 4:00 | targeting-rules | Put a second person between a deployment request and a deployment, with the blast radius, diff and policy in view. |
| `ship-safely/safety-nets.mdx` | Safety nets | — | 2 | 11, 4:00 | approvals-and-policies, automation-and-ci | Block planned change with a freeze window, override a live flag with the kill switch, cancel a scheduled change, and roll back from version history. |
| `integrations/jira-setup.mdx` | Jira setup | — | 1 | 12, 4:00 | approvals-and-policies | Connect Jira Cloud so that a ticket status change can request, approve and deploy a release. |
| `integrations/jira-end-to-end.mdx` | Jira end to end | — | 2 | 13, 4:00 | jira-setup | Move a Jira ticket through review and approval, and watch FluxGate deploy the release and report back on the ticket. |
| `integrations/jev-ai-assistance.mdx` | Jev AI assistance | Jev AI | 3 | 14, 4:00 | approvals-and-policies | Use TypeSafe Jev to catch vague reasons, rate approval risk, classify flags, and search in plain English, while people make every decision. |
| `integrations/sso.mdx` | Single sign-on | SSO | 4 | — | teams-users-roles | Sign users in through your OpenID Connect provider, map groups to FluxGate roles, and keep a break-glass admin. |
| `observe-and-operate/dashboards.mdx` | Dashboards | — | 1 | 15, 3:30 | clients-and-edge-server | Read evaluation volume, variant performance, and the audit trail to decide whether a rollout worked. |
| `observe-and-operate/going-to-production.mdx` | Going to production | — | 2 | 16, 3:30 | install | Run FluxGate in production with pinned images, a managed database, two secrets, TLS, a nearby edge server, single sign-on, and a rotatable JWT secret. |
| `developer-guide.mdx` | Developer guide | — | 1 | — | — | Set up your own FluxGate installation, from an empty folder to a first flag evaluation, by copying commands from this page. |
| `reference/configuration.mdx` | Configuration reference | Configuration | 1 | — | — | Every setting of the backend, edge server and UI images: config.toml keys and environment variables, with defaults. |
| `reference/edge-api.mdx` | Edge server API | Edge API and OFREP | 2 | — | — | Evaluate flags over HTTP: the /evaluate endpoint, the OFREP endpoints, SDK keys, CORS, ETags, and error codes. |
| `reference/sdks.mdx` | SDKs and integrations | SDKs | 3 | — | — | Use the OpenFeature SDKs with the OFREP provider, call the edge server over plain HTTP, or use the Spring Boot starter when it is released. |

`chapter` is the folder name (`overview` for `index.mdx`, `developer-guide` for `developer-guide.mdx`). For pages with a video, `takeaway` is the "Takeaway" row of the matching script header in `../docs/demo-videos/NN-*.md`, copied verbatim. Pages without a video get a one-sentence `takeaway` of your own in the same style. `reference/sdks.mdx` also gets `badge: coming-soon` only if the whole page is about unreleased software; it is not, so leave `badge` off and mark the starter section with a `<Callout type="note" title="Coming soon">` instead.

- [ ] **Step 1: Write `docs/AUTHORING.md`**

````markdown
# Writing FluxGate docs

Docs pages are MDX files in `src/content/docs/<chapter>/<slug>.mdx`. The file location sets the URL (`/docs/<chapter>/<slug>/`). Frontmatter sets everything the sidebar, header, search, and SEO need.

## Sources

Each chapter page matches one demo video. Its script, `docs/demo-videos/NN-*.md` in the FluxGate monorepo, is the source of truth for UI labels and behavior: the scripts were dry-run tested against the `v1.2.0` images. When the script and the older wiki disagree, the script wins. When neither covers a claim, check it on a running `v1.2.0` stack or leave it out.

## Frontmatter

```yaml
title: Targeting rules            # page h1 and <title>
navTitle: Targeting               # optional, shorter sidebar label
description: One sentence, 120-160 characters, for search results and SEO.
chapter: model-your-release       # must equal the folder name
order: 4                          # position inside the chapter
takeaway: The script header "Takeaway", verbatim.
video:
  number: 7                       # demo video number; the YouTube id lives in src/content/videos.ts
  length: "4:00"                  # the script header "Length target"
prerequisites: [first-feature]    # doc ids (file names without .mdx)
```

The page header (title, takeaway, video length, "Builds on" links) and the video are rendered by the layout. Do not repeat them in the body. Do not write an `# h1`.

## Page sections, in this order

1. `## Before you start`: the script's "Start state" and "Prerequisites" rewritten for a reader: what must exist, which user to sign in as (with `<RoleBadge>`), which team to select.
2. `## <Concept heading>` (one or more): what the feature is and why it exists. More depth than the voiceover. Use the voiceover as raw material, not as text to copy.
3. `## <Task heading>`: numbered steps from the scene table inside `<Steps>`. One action per step. Exact UI labels in **bold**. Routes in code (`/contexts`). Expected results ("The toast "Context created" appears").
4. `## Examples` or task-specific example headings: concrete artifacts: JSON a rule or request uses, `curl` calls with real responses, policy tables, `.env` lines.
5. `## Good to know`: the script's "Gotchas" rewritten for users. Keep product behavior and limits. Remove anything about recording, voiceover, file paths, line numbers, source code, or internal rulings.
6. `## Troubleshooting` (only when the script gotchas or `docs/product-bugs/2026-10-demo-recording.md` describe something a user can hit): `### <symptom>` then the fix.
7. `## Next`: one sentence from the script "Hand-off" with a link to the next page.

## Components

```mdx
<Steps>

1. Click **Contexts** under **Build**.
2. Click **Create New Context**.

</Steps>

<Callout type="note|tip|warn" title="Optional title">
Text. Leave blank lines around Markdown inside components.
</Callout>

<CodeTabs labels={['curl', 'JavaScript']}>

```bash
curl ...
```

```js
await client.getStringValue(...)
```

</CodeTabs>

Sign in as `priya` <RoleBadge role="requester" />. Roles: admin, team-admin, requester, approver.
```

Code fences take an optional title: ```` ```bash title="Start the edge server" ````. Every fence needs a language (`bash`, `json`, `js`, `yaml`, `toml`, `text`, `http`).

## Content rules

- Public artifacts only: images `keaz/flux-gate-backend`, `keaz/flux-gate-edge`, `keaz/flux-gate-ui` at `v1.2.0`; the two downloads `/downloads/docker-compose.demo.yml` and `/downloads/config.demo.toml`. No source checkout, no local builds, no `fluxgate` CLI.
- No private references: no source file names with line numbers, no internal repository names, no "controller ruling", no recording notes.
- Keep the story: Juniper Market, team `Checkout`, `express-checkout` (variants `classic` and `express`), `holiday-banner`, users `admin`, `priya` (Requester), `sam` (Approver), environments Development, Staging, Production, pipeline `checkout-release`, contexts `country` and `user_tier`, clients `juniper-web` and `checkout-service`, Jira project `CHK`, ticket `CHK-142`.
- Secrets are placeholders in angle brackets: `<checkout-service API key>`. Never paste a real key.
- Write in plain technical English: short sentences, active voice, present tense, imperative for instructions, one term for one thing.
- Links to other docs pages use absolute paths with a trailing slash: `/docs/connect-your-app/clients-and-edge-server/`.

## Checks before you commit

```bash
pnpm check:docs   # private references, CLI, image tags, links, draft markers
pnpm build        # schema, registry, prerender, dist check, search index
```

Then open the page with `pnpm preview` in light and dark mode at desktop and phone width.
````

- [ ] **Step 2: Scaffold every page in the table**

For each row except `index.mdx` and `model-your-release/contexts.mdx`, create the file with its frontmatter and this body, filled from the script header (or, for pages without a video, from the source named in their later task):

```mdx
## Before you start

- <start state from the script header, rewritten as what must already exist>
- <who to sign in as, with RoleBadge, and the team to select>

## What you will do

<two to four sentences that expand the takeaway: the problem this page solves and the result the reader ends with>

## Next

<the script's Hand-off sentence, with a link to the next page>
```

The angle-bracket lines above are instructions for you, not text to keep: every scaffold must read as finished, if short, content. The article text must be at least 200 characters (the layout header, takeaway, and video placeholder count toward that), or `check-dist` fails.

Example, `src/content/docs/model-your-release/targeting-rules.mdx`:

```mdx
---
title: Targeting rules
description: Serve a variant to one segment first, then split everyone else by percentage, and understand why rule order matters.
chapter: model-your-release
order: 4
takeaway: You can target Canadian Plus users first, then split everyone else 20/80.
video:
  number: 7
  length: "4:00"
prerequisites: [first-feature]
---

## Before you start

- The feature `express-checkout` exists with the variants `classic` and `express`, and its stages have no criteria yet.
- The approval policy `Release approvals` exists.
- Sign in as `admin` <RoleBadge role="admin" />, and select the team **Checkout** in **Select team**.

## What you will do

Canadian Plus users get express checkout first, and everyone else gets it for one user in five. That takes two criteria on each stage, and the order in which FluxGate checks them decides whether the plan works. You then request a deployment of the Development stage, and an approver signs it off.

## Next

Connect a real app to the edge server and evaluate `express-checkout` in [Clients and edge server](/docs/connect-your-app/clients-and-edge-server/).
```

- [ ] **Step 3: Write the complete exemplar `model-your-release/contexts.mdx`**

This page is the reference for every later content task. It is built from `../docs/demo-videos/05-contexts.md`.

````mdx
---
title: Contexts
description: Declare the facts your targeting rules use, such as country and user tier, and send them from your app at evaluation time.
chapter: model-your-release
order: 2
takeaway: You declare the facts a rule can use, `country` and `user_tier`, and see how your app sends them at evaluation time.
video:
  number: 5
  length: "2:30"
prerequisites: [environments-and-pipelines]
---

## Before you start

- The environments Development, Staging and Production and the pipeline `checkout-release` exist. See [Environments and pipelines](/docs/model-your-release/environments-and-pipelines/).
- Sign in as `priya` <RoleBadge role="requester" />. Creating a context needs no special role.
- Select the team **Checkout** in **Select team**.

## What a context is

FluxGate cannot know a user's country or plan. Your app knows, and it sends those facts with every evaluation. A **context** declares one such fact: a key, such as `country`, and the values your app is expected to send, such as `US`, `CA` and `UK`.

Contexts help in two places:

- The rule editor suggests context keys, so you pick `country` instead of typing it again.
- The **In List** operator can use a whole context as its list of values.

A context does not restrict anything. A rule can still use a key that you never declared, and your app can send values that are not in the list.

## Create the contexts

<Steps>

1. Click **Contexts** under **Build** to open `/contexts`. The page reads "Define context variables for targeting rules".
2. Click **Create New Context**. The page **Create Context** opens.
3. In **Context Key**, type `country`. Use exactly the spelling your app sends.
4. Under **Context Values**, type `US` in the empty field. Click **Add Value**, click the new field below it, and type `CA`. Do the same for `UK`.
5. Click **Save Context**. The toast "Context created" appears and the list at `/contexts` shows `country`.
6. Repeat for the key `user_tier` with the values `free` and `plus`.

</Steps>

The list shows only the **Key** column. Open a context to see its values again.

## What your app sends

When your app asks for a flag, it sends an evaluation context. Its keys match the contexts you declared, plus a bucketing key:

```json title="Evaluation context"
{
  "bucketingKey": "user-42",
  "country": "CA",
  "user_tier": "plus"
}
```

[Clients and edge server](/docs/connect-your-app/clients-and-edge-server/) sends this context to the edge server for real.

### The bucketing key

The bucketing key is a stable identifier for the user. For a percentage split, FluxGate hashes the flag key together with the bucketing key to choose a bucket:

```text title="How a bucket is chosen"
bucket = SHA-256("<flag key>:<bucketing key>")
```

The same user lands in the same bucket every time, so nobody switches between checkout versions when they reload the page.

<Callout type="warn" title="Use a stable key">
Use a user ID or an account ID. Do not use a session ID or a random number: the user would get a new bucket for every session or request.
</Callout>

<Callout type="note">
A weighted split cannot place a request that has no bucketing key.
</Callout>

## Good to know

- Any signed-in user can create a context. Editing an existing context needs a system admin or a **Team Admin**.
- The value fields have no labels, only the placeholder "e.g., admin, US, mobile". A remove button appears when you point at a value.
- Add contexts when a rule needs a new fact, for example `app_version` or `device_type`.

## Next

Create the `express-checkout` flag, its variants and its pipeline in [Create your first feature](/docs/model-your-release/first-feature/).
````

- [ ] **Step 4: Write the full docs landing `index.mdx`**

Keep its frontmatter from Task 7. Body:

```mdx
FluxGate separates deploying code from releasing a feature. You ship code with the feature switched off, then decide who sees it, when, and with whose approval, without another deploy.

These docs follow one story from install to production. The Checkout team at Juniper Market, an online grocery, wants to roll out a one-tap **express checkout** safely: Plus users in Canada first, then a 20/80 split for everyone else, gated by approvals, driven from Jira, with an AI assistant flagging risky changes. Every chapter has a short video and a written guide with the details and examples the video has no time for.

## Start here

- **Want it running now?** Follow the [developer guide](/docs/developer-guide/): an empty folder to a first flag evaluation, by copying commands.
- **Want to understand it first?** Read [What is FluxGate](/docs/get-started/what-is-fluxgate/), then follow the chapters in order. Each page builds on the one before.

## The cast

| User | Role in the story | FluxGate role |
|---|---|---|
| `admin` | Platform admin | System admin |
| `priya` | Checkout developer | Requester |
| `sam` | Release manager | Approver |

## Get started

Install FluxGate and set up who can do what.

- [What is FluxGate](/docs/get-started/what-is-fluxgate/): the moving parts and why deploy and release are separate.
- [Install and first boot](/docs/get-started/install/): Docker Compose and the first admin.
- [Teams, users and roles](/docs/get-started/teams-users-roles/): a team, a requester, an approver.

## Model your release

Describe where code runs, what your app knows about a user, and what you release.

- [Environments and pipelines](/docs/model-your-release/environments-and-pipelines/)
- [Contexts](/docs/model-your-release/contexts/)
- [Create your first feature](/docs/model-your-release/first-feature/)
- [Targeting rules](/docs/model-your-release/targeting-rules/)

## Connect your app

- [Clients and edge server](/docs/connect-your-app/clients-and-edge-server/): curl, OFREP, and the OpenFeature SDK.
- [Automation and CI](/docs/connect-your-app/automation-and-ci/): a build gate on a flag.

## Ship safely

- [Approvals and policies](/docs/ship-safely/approvals-and-policies/)
- [Safety nets](/docs/ship-safely/safety-nets/): freeze windows, kill switch, scheduled changes, rollback.

## Integrations

- [Jira setup](/docs/integrations/jira-setup/) and [Jira end to end](/docs/integrations/jira-end-to-end/)
- [Jev AI assistance](/docs/integrations/jev-ai-assistance/)
- [Single sign-on](/docs/integrations/sso/)

## Observe and operate

- [Dashboards](/docs/observe-and-operate/dashboards/)
- [Going to production](/docs/observe-and-operate/going-to-production/)

## Developer guide

The copy-paste path from an empty folder to a running FluxGate: [Developer guide](/docs/developer-guide/).

## Reference

- [Configuration reference](/docs/reference/configuration/)
- [Edge server API](/docs/reference/edge-api/)
- [SDKs and integrations](/docs/reference/sdks/)
```

The h2 headings equal the chapter titles, so their ids (`get-started`, `model-your-release`, …) match the breadcrumb anchors `/docs/#<chapter>` used in the JSON-LD.

- [ ] **Step 5: Build and check**

Run: `pnpm check:docs && pnpm build`
Expected: `check-docs: 22 pages OK`; `check-dist: 26 pages OK` (4 product + 22 docs).

Open `/docs/`, `/docs/model-your-release/contexts/`, and two scaffold pages in `pnpm preview`. Check the sidebar order matches the table, the "Builds on" chips link correctly, and the contexts page renders steps, both callouts, and both code blocks with titles.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: authoring guide, page scaffold, landing, and contexts page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Get started chapter

**Files:**
- Modify: `src/content/docs/get-started/what-is-fluxgate.mdx`, `install.mdx`, `teams-users-roles.mdx`

**Sources:** `../docs/demo-videos/01-what-is-fluxgate.md`, `02-install-and-first-boot.md`, `03-teams-users-roles.md`, `../docs/demo-videos/README.md` (recording setup section), `../docs/demo-videos/assets/*`, `../docs/product-bugs/2026-10-demo-recording.md`.

Write each page in full, following `docs/AUTHORING.md` and the exemplar `contexts.mdx`. Page-specific requirements:

**`what-is-fluxgate.mdx`**
- Concepts: deploy versus release; the four services (admin UI, backend with PostgreSQL, edge server, your app with an SDK) and what flows between them (REST and WebSocket from the UI, gRPC stream from backend to edge, evaluations from apps to the edge, telemetry back). Include a `text` diagram or a table of the services with their default ports from the demo compose file (UI 3000, backend 8080 REST, backend 50051 gRPC, edge 8081, PostgreSQL 5433 on the host).
- A short tour of the sidebar groups the UI shows (taken from the script scenes).
- No `## Steps` section is needed; this page is conceptual.

**`install.mdx`**
- Steps from the scene table: download the two files from `/downloads/docker-compose.demo.yml` and `/downloads/config.demo.toml` into an empty folder, generate the encryption key into `.env`, `docker compose -f docker-compose.demo.yml up -d`, open `http://localhost:3000`, create the first admin.
- Examples: the exact commands with titles, the expected `docker compose ... ps` output shape, and the `.env` content after this page (`FLUXGATE_ENCRYPTION_KEY=<base64 of 32 bytes>`).
- `<Callout type="warn">`: never change `FLUXGATE_ENCRYPTION_KEY` while the database lives; it encrypts Jira write-back tokens and SSO secrets.
- Good to know: data lives in the `pgdata` volume (`down` keeps it, `down -v` deletes it); the UI calls the backend directly at `localhost:8080`, so port 8080 must be free; Swagger UI at `http://localhost:8080/docs`.
- Troubleshooting from the script gotchas (for example: the `FLUXGATE_ENCRYPTION_KEY` error message from compose when `.env` is missing, ports already in use).

**`teams-users-roles.mdx`**
- Concepts: a table of the three system roles and what each allows, plus **Team Admin**, from the script and its gotchas. Explain temporary passwords and the first sign-in flow ("Update Your Password").
- Steps: create team `Checkout`, create users `priya` (Requester) and `sam` (Approver), add them to the team.
- Good to know: requesters cannot approve their own request; the first sign-in of a new user lands on "Update Your Password".

- [ ] **Step 1: Read the three scripts and the product bugs file in full.**
- [ ] **Step 2: Write `what-is-fluxgate.mdx`.**
- [ ] **Step 3: Write `install.mdx`.**
- [ ] **Step 4: Write `teams-users-roles.mdx`.**
- [ ] **Step 5: Verify every command on a clean stack.** In a new empty folder (for example `/private/tmp/fluxgate-docs-check`), run each command from `install.mdx` exactly as written, with the downloads served by `pnpm preview` (`curl -fsSLO http://localhost:4173/downloads/docker-compose.demo.yml` and the same for `config.demo.toml`). Sign in to `http://localhost:3000` with the built-in browser and confirm each UI label on all three pages. Fix the page, not the stack, when they disagree. Leave this stack running for Task 14.
- [ ] **Step 6: Build and check.** Run `pnpm check:docs && pnpm build`; expected both pass. Review the three pages in `pnpm preview`.
- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: get started chapter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Developer guide

**Files:**
- Modify: `src/content/docs/developer-guide.mdx`

**Sources:** `../docs/demo-videos/assets/docker-compose.demo.yml`, `config.demo.toml`, scripts 02, 03, 05, 06, 07, 08, 14, 16 (for the optional steps), `../feature-toggle/docs/edge-server-api.md`.

The developer guide is a runbook. Each section ends with a check the reader can run, and a "Learn more" link to the chapter page.

Required sections and content:

1. `## Prerequisites`: Docker with Compose v2; `openssl`; `curl` and `jq` for checks; Node 20+ only for the SDK example. Free ports 3000, 8080, 8081, 5433.
2. `## 1. Get the files`: `mkdir fluxgate && cd fluxgate`, then `curl -fsSLO https://flux.forgeopslabs.com/downloads/docker-compose.demo.yml` and the same for `config.demo.toml`. Check: `ls` shows both.
3. `## 2. Create the encryption key`: `echo "FLUXGATE_ENCRYPTION_KEY=$(openssl rand -base64 32)" > .env`, with the warning callout from Task 13.
4. `## 3. Start FluxGate`: `docker compose -f docker-compose.demo.yml up -d`; check `docker compose -f docker-compose.demo.yml ps` and `curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/docs/` (use the health or docs URL the script uses; verify it returns 200).
5. `## 4. Create the first admin`: open `http://localhost:3000`, **Create Admin**. Learn more: Install.
6. `## 5. Create a team, an environment, and a flag`: minimal path (one team, one environment, one SIMPLE or CONTEXTUAL flag with two variants, one stage deployed). Link the chapter pages for depth instead of repeating them.
7. `## 6. Create a client and start the edge server`: create a Backend client, copy its client ID and API key, `echo EDGE_CLIENT_ID=... >> .env`, `echo EDGE_CLIENT_SECRET=... >> .env`, `docker compose -f docker-compose.demo.yml --profile edge up -d edge`, check `/health` returns 200.
8. `## 7. Evaluate a flag`: `<CodeTabs labels={['curl /evaluate', 'curl OFREP', 'OpenFeature (Node)']}>` with the three blocks from script 08's "Code on screen" (blocks B, D, E), adapted to the reader's flag key, each followed by a real response captured from your stack.
9. `## 8. Optional: AI assistance, Jira, single sign-on`: `echo TYPESAFE_API_KEY=... >> .env` then `docker compose -f docker-compose.demo.yml up -d backend`; links to Jev, Jira setup, SSO pages.
10. `## 9. Before production`: a checklist linking to [Going to production](/docs/observe-and-operate/going-to-production/).
11. `## Reset or remove`: `docker compose -f docker-compose.demo.yml down` keeps data; `down -v` deletes it (warn callout).

- [ ] **Step 1: Write the page.**
- [ ] **Step 2: Run the guide end to end, copy-pasting from the rendered page.** Stop the Task 13 stack with `down -v`. Build and `pnpm preview` the site. In a new empty folder, copy every command from the rendered `/docs/developer-guide/` page in the built-in browser (use each code block's Copy button text) and run it. The download URLs point at production, which does not have the files yet; for this run, replace `https://flux.forgeopslabs.com` with `http://localhost:4173` only on the command line, not in the page. Capture the real responses for section 7 and paste them into the page with secrets replaced by placeholders.
- [ ] **Step 3: Record what failed.** Any step that did not work as written is fixed in the page. A product bug (the product misbehaves, not the docs) is appended to `../docs/product-bugs/2026-10-demo-recording.md` in the monorepo with steps to reproduce, and committed there separately on `main` of the monorepo.
- [ ] **Step 4: Build and check.** `pnpm check:docs && pnpm build`.
- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: developer guide from empty folder to first evaluation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Leave the stack running with the data from this task; Tasks 15–19 build on it.

---

# Phase 4 — Chapter content

Each task below writes complete pages, replacing the scaffold. For every page:

1. Read its script in full, plus the product bugs file.
2. Write it following `docs/AUTHORING.md` and the exemplar `contexts.mdx`.
3. Walk the steps on the running stack from Task 14 with the built-in browser, as the script's users, and fix any label or behavior that differs. Create the story data as you go (it is reused for screenshots in Task 22).
4. For every command or request in the page, run it and paste the real response (secrets replaced by placeholders).
5. `pnpm check:docs && pnpm build`, review in `pnpm preview` (light, dark, 375 px), commit.

### Task 15: Model your release chapter

**Files:** Modify `src/content/docs/model-your-release/environments-and-pipelines.mdx`, `first-feature.mdx`, `targeting-rules.mdx` (`contexts.mdx` is done).

**Sources:** scripts 04, 06, 07.

Page-specific requirements:

- **`environments-and-pipelines.mdx`**: concepts for environment types (Development, Staging, Production), pipelines as ordered stages, and why the approval policy `Release approvals` is created here (without a policy a stage cannot reach DEPLOYED through the UI: "Request Deployment" would stop at DEPLOYMENT_REQUESTED). Steps for the three environments, the `checkout-release` pipeline, and the policy. Example: a table of the policy fields and the values used.
- **`first-feature.mdx`**: concepts for feature types (SIMPLE, CONTEXTUAL), kinds (release and others the UI offers), variants and their value types, owner, tags, ticket / Reference URL. Steps for `express-checkout` and `holiday-banner`. Example: the variant table (`classic`, `express`, String). Explain the feature list columns and the detail page.
- **`targeting-rules.mdx`**: concepts: a criterion pairs a rule with a variant; "Specific Variant" versus "Weighted Split"; rule groups (AND within a group, OR between groups); a criterion without rule groups matches everyone; priorities start at 0, lower is checked first, first match wins; the "Reachable" badge. Steps for both criteria on Development and Staging, saving, the rollout template, and the request → approve → deploy loop with `priya`, `sam`, `priya`. Examples: an evaluation walk-through table (three users: CA plus, CA free, US free → which criterion matches → which variant); the 100-user split result from script 08 block C as a preview of what 20/80 looks like. Good to know: "Specific Variant" preselects the first variant; switching stage discards unsaved criteria; a rollout template stores the stage plan, not criteria; saving a template needs an admin or Team Admin; weights must total 100 and need at least two weighted variants.

- [ ] **Step 1: Write and verify `environments-and-pipelines.mdx`.**
- [ ] **Step 2: Write and verify `first-feature.mdx`.**
- [ ] **Step 3: Write and verify `targeting-rules.mdx`.**
- [ ] **Step 4: Build, review, commit** (`docs: model your release chapter`, with the Co-Authored-By trailer).

### Task 16: Connect your app chapter

**Files:** Modify `src/content/docs/connect-your-app/clients-and-edge-server.mdx`, `automation-and-ci.mdx`.

**Sources:** scripts 08, 09 (including their "Code on screen" sections), `../feature-toggle/docs/edge-server-api.md`.

- **`clients-and-edge-server.mdx`**: concepts: client types (Web, Backend), SDK key format `<clientId>.<apiKey>`, web origins and CORS for Web clients, the edge server's in-memory cache and gRPC stream, `/evaluate` (edge-configured client) versus OFREP (SDK key). Steps for clients `juniper-web` and `checkout-service`, `.env` edge credentials, starting the edge. Examples from script blocks A–E with real responses; the ETag `304` round trip; the 100-user split count. Link [Edge server API](/docs/reference/edge-api/) and [SDKs](/docs/reference/sdks/).
- **`automation-and-ci.mdx`**: concepts: System Clients and scoped tokens for automation, why CI should not use a person's account. Steps from the script. Examples: the `gate.sh` script from "Code on screen", a GitHub Actions job that runs it (write a minimal `.github/workflows/flag-gate.yml` example using `curl` and `jq` only; mark it as an example), and the exit codes.

- [ ] **Step 1: Write and verify `clients-and-edge-server.mdx`.**
- [ ] **Step 2: Write and verify `automation-and-ci.mdx`.** Run `gate.sh` against the stack for both flag states and paste both outputs.
- [ ] **Step 3: Build, review, commit** (`docs: connect your app chapter`).

### Task 17: Ship safely chapter

**Files:** Modify `src/content/docs/ship-safely/approvals-and-policies.mdx`, `safety-nets.mdx`.

**Sources:** scripts 10, 11.

- **`approvals-and-policies.mdx`**: concepts: policy scope (which environments), required approvals and roles, self-approval rule, request lifecycle (DEPLOYMENT_REQUESTED → DEPLOYMENT_APPROVED / DEPLOYMENT_REJECTED → DEPLOYED), what the approver sees (blast radius, diff, snapshot, policy). Steps: the policy tour, a Staging request approved, a Production request rejected with a comment. Example: a state table of the stage statuses and who can move each.
- **`safety-nets.mdx`**: concepts for freeze windows, kill switch, scheduled changes, version history and rollback, and how they interact with approvals. Steps per script. Example: the CI gate from Task 16 run during a freeze, with its output.

- [ ] **Step 1: Write and verify `approvals-and-policies.mdx`.**
- [ ] **Step 2: Write and verify `safety-nets.mdx`.**
- [ ] **Step 3: Build, review, commit** (`docs: ship safely chapter`).

### Task 18: Integrations chapter

**Files:** Modify `src/content/docs/integrations/jira-setup.mdx`, `jira-end-to-end.mdx`, `jev-ai-assistance.mdx`, `sso.mdx`.

**Sources:** scripts 12, 13, 14, 16 (SSO scenes); `../feature-toggle/docs/sso.md` (skip its "Command line login" section entirely; the CLI is not public).

- **`jira-setup.mdx`**: concepts: the public Events URL (and a tunnel when running locally), the Jira Automation flow, status rules (In Review → request, Approved → approve, Done → deploy), trusted approvals, the write-back token (encrypted with `FLUXGATE_ENCRYPTION_KEY`). Steps per script. Examples: the Jira Automation web request (URL, headers, body) exactly as the script configures it with secrets as placeholders; the tunnel command `ngrok http --host-header=localhost 8080 --pooling-enabled`.
- **`jira-end-to-end.mdx`**: steps per script; an example timeline table: Jira status → FluxGate stage status → comment FluxGate writes back.
- **`jev-ai-assistance.mdx`**: concepts: what Jev does and does not do (advice, never decisions); enabling it with `TYPESAFE_API_KEY` and recreating only the backend; each feature (reason quality warning, approval risk rating, flag kind classification, plain-English search). Steps per script. Good to know: without the key, all AI UI stays hidden.
- **`sso.mdx`** (no video; frontmatter has no `video`): built from `sso.md` and script 16: how an OIDC login works (short), backend settings (`public_base_url` in `config.toml`, and any other keys `sso.md` lists), the redirect URI to register, the admin UI walkthrough steps 1–7, who may sign in, group mapping and role sync, enforcing SSO with a break-glass admin, security notes, and the Keycloak, Okta, and Microsoft Entra ID recipes. Verify the UI steps on the stack with the built-in browser up to the point that needs a real identity provider; do not sign in to any third-party identity provider.

- [ ] **Step 1: Write and verify `jira-setup.mdx`.** No Jira Cloud sandbox is available to you: verify the FluxGate side (Integrations page labels, generated URLs) on the stack, and take the Jira side verbatim from the script, which was recorded against a real sandbox.
- [ ] **Step 2: Write `jira-end-to-end.mdx`** (same verification limits).
- [ ] **Step 3: Write and verify `jev-ai-assistance.mdx`.** Verify only that the AI UI is hidden without `TYPESAFE_API_KEY`; take the AI responses from the script. Do not ask for or use a TypeSafe key.
- [ ] **Step 4: Write and verify `sso.mdx`.**
- [ ] **Step 5: Build, review, commit** (`docs: integrations chapter`).

### Task 19: Observe and operate chapter

**Files:** Modify `src/content/docs/observe-and-operate/dashboards.mdx`, `going-to-production.mdx`.

**Sources:** scripts 15, 16 (including "Code on screen"); `../docs/demo-videos/assets/docker-compose.demo.yml` as the base for the production example.

- **`dashboards.mdx`**: concepts for each of the four dashboards in the script, custom metrics (`checkout_conversion`), and how to read a variant comparison. Steps per script. Example: posting metric events (the request from the script with a real response). Generate evaluations for the screenshots with the loop from script 08 block C run for both flags.
- **`going-to-production.mdx`**: a production checklist and a production compose example derived from the demo compose file: pinned `v1.2.0` images, external managed PostgreSQL via `DATABASE_URL`, `FLUXGATE_ENCRYPTION_KEY` and the JWT secret from a secret store, no published PostgreSQL port, TLS terminated at a reverse proxy, `public_base_url` set, `allowed_origin` set to the real UI origin, the edge server deployed near the apps. Steps per script for SSO and JWT secret rotation. Mark the compose file as an example to adapt.

- [ ] **Step 1: Write and verify `dashboards.mdx`.**
- [ ] **Step 2: Write `going-to-production.mdx`** and validate the example compose file with `docker compose -f <file> config` (expected: no errors, with dummy env values).
- [ ] **Step 3: Build, review, commit** (`docs: observe and operate chapter`).

---

# Phase 5 — Reference

### Task 20: Configuration reference

**Files:** Modify `src/content/docs/reference/configuration.mdx`.

**Sources:** `../docs/demo-videos/assets/config.demo.toml`, `../docs/demo-videos/assets/docker-compose.demo.yml`, `../feature-toggle/config.toml`, `../feature-toggle/DOCKER.md`, `../feature-toggle-ui/DOCKER_DEPLOYMENT.md`, `../feature-toggle-ui/docker-entrypoint.sh`, `../feature-toggle/docs/edge-server-api.md` (edge cache settings), `../feature-toggle/docs/sso.md` (backend SSO settings), script 16.

Structure:

- `## Backend`: `### config.toml` table (key, default, description) for every key the backend reads; `### Environment variables` table (`DATABASE_URL`, `FLUXGATE_ENCRYPTION_KEY`, `TYPESAFE_API_KEY`, `RUST_LOG`, and any other variable the sources list, with which ones override `config.toml`). Note that the image copies `/app/config/config.toml` to `/app/config.toml` at start.
- `## Edge server`: environment variables (`EDGE_BACKEND_GRPC`, `EDGE_HTTP_ADDR`, `EDGE_CLIENT_ID`, `EDGE_CLIENT_SECRET`, cache TTLs) with defaults.
- `## Admin UI`: `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_PROTOCOL`, `WS_PROTOCOL`, explaining that the browser calls the backend directly.
- `## Ports`: a table of every port.
- `## Secrets`: which values are secrets, how to generate them, and what breaks when they change.

Every default must be checked in a running container, not only read from a file: `docker compose -f docker-compose.demo.yml exec backend cat /app/config.toml` and `docker compose -f docker-compose.demo.yml exec edge env` (redact secrets in anything you paste). Leave out any key you cannot confirm.

- [ ] **Step 1: Collect and confirm every setting.**
- [ ] **Step 2: Write the page.**
- [ ] **Step 3: Build, review, commit** (`docs: configuration reference`).

### Task 21: Edge API and SDK reference

**Files:** Modify `src/content/docs/reference/edge-api.mdx`, `src/content/docs/reference/sdks.mdx`.

**Sources:** `../feature-toggle/docs/edge-server-api.md` (current; wins over the wiki), `../fluxgate.wiki/Edge-Server-API.md` (older examples, verify before use), script 08, `../fluxgate-springboot/README.md`, the edge Swagger UI at `http://localhost:8081/docs` on the running stack.

- **`edge-api.mdx`**: `## Authentication` (SDK key format and headers, the status/`errorCode` table, auth caching behavior); `## CORS`; `## Endpoints` with one `###` per endpoint (`GET /health`, `POST /evaluate`, `POST /ofrep/v1/evaluate/flags/{key}`, `POST /ofrep/v1/evaluate/flags`), each with request, response, and errors; `## ETags and caching`; `## Evaluation reasons`; `## Swagger UI` (`http://localhost:8081/docs`, `/api-doc/openapi.json`). Run every example against the stack with `express-checkout` and paste the real responses.
- **`sdks.mdx`**: `## OpenFeature with OFREP` (recommended path) with `<CodeTabs labels={['Node (server)', 'Browser (web)', 'Java']}>`: Node from script 08 block E; browser with `@openfeature/web-sdk` and `@openfeature/ofrep-web-provider` against a Web client (note the web origin requirement); Java with the OpenFeature Java SDK and its OFREP provider (`dev.openfeature.contrib.providers:ofrep`). Run the Node and browser examples against the stack (the browser one from a page served on an allowed origin, for example `http://localhost:5173` via a tiny `pnpm dlx vite` folder outside the repo); state the exact package versions you used. Compile-check the Java example only if a JDK is available, otherwise mark its version line as the one you checked on Maven Central. `## Plain HTTP` (short, links to the edge API page). `## Spring Boot starter` inside `<Callout type="note" title="Coming soon">`: what it will offer (from the README feature list), and that it is not published yet; do not show Maven coordinates.

- [ ] **Step 1: Write and verify `edge-api.mdx`.**
- [ ] **Step 2: Write and verify `sdks.mdx`.**
- [ ] **Step 3: Build, review, commit** (`docs: edge API and SDK reference`).

---

# Phase 6 — Product site

### Task 22: Screenshot retakes

**Files:**
- Create: `public/images/ui/<name>-light.jpg` and `public/images/ui/<name>-dark.jpg` for each name below

**Interfaces:**
- Produces: image paths used by Task 23: `system-overview`, `features-list`, `stage-editor`, `approvals`, `dashboards`.

| Name | Screen | State to show |
|---|---|---|
| `system-overview` | `/` after sign-in as `admin` | Checkout team selected, activity from the docs walk-through |
| `features-list` | `/features` | `express-checkout` and `holiday-banner` |
| `stage-editor` | `/features/:id/edit`, Development stage selected, both criteria expanded | CA + plus → `express`; 20/80 split |
| `approvals` | `/approvals` | one pending request with "Details" open |
| `dashboards` | the evaluation dashboard from script 15 | traffic from the block C loop for both flags |

- [ ] **Step 1: Prepare the state.** Use the stack and data from Tasks 14–19. Generate evaluation traffic with the script 08 block C loop (run it a few times for both flags). Create one pending approval request as `priya` if none is pending.
- [ ] **Step 2: Capture.** In the built-in browser, set the viewport to 1440×900 with `resize_window`, colorScheme light, zoom 100%. For each screen take a screenshot; switch the FluxGate UI theme with its own theme toggle and the browser color scheme to dark, and capture again. Save PNGs to the scratchpad.
- [ ] **Step 3: Convert and size.** For each PNG: `sips -s format jpeg -s formatOptions 82 --resampleWidth 1600 <in>.png --out public/images/ui/<name>-<theme>.jpg`. Expected: each file under 350 KB (`ls -la public/images/ui`). Check no secret (API key, password) is visible in any image; retake if one is.
- [ ] **Step 4: Commit** (`assets: retake UI screenshots in light and dark`).

### Task 23: Home page rewrite

**Files:**
- Modify: `src/pages/HomePage.tsx`, `src/pages/shared-content.ts`, `src/pages/pages.test.tsx`, `src/site.ts` (home meta description and FAQ JSON-LD)

**Interfaces:**
- Consumes: `ThemedImage` (Task 2), primitives (Task 3), `ArchitectureDiagram` (Task 4), `VideoEmbed`, `getVideo` (Tasks 7–8), `TerminalBlock` (Task 2), `CHAPTERS` (Task 6), screenshots (Task 22).
- Produces: `HomePage()`; `chapterCards` and the new `faqs` in `shared-content.ts`.

Sections, in order:

1. **Hero** (`<section>` with `--accent-glow` blur, like `PageHero`): eyebrow "Feature flag delivery platform"; h1 "Ship code anytime. Release features when they are ready."; text "FluxGate is a self-hosted feature flag platform with governed rollouts, approvals, a Rust edge server, and OpenFeature-ready evaluation."; buttons "Get started" (`/docs/get-started/install/`) and "Watch the overview" (`#overview`, secondary); chips "Self-hosted", "Rust edge server", "OpenFeature OFREP", "Approvals and audit". Right column: `ThemedImage` of `system-overview` in a browser-frame card (`rounded-xl border border-border bg-card shadow-card-hover`, a 36 px top bar with three dots).
2. **Proof bar**: the existing `proofStats` as `MetricCard`s.
3. **From install to production** (`id="journey"`): six cards, one per numbered chapter, from `chapterCards` (`{ chapter: ChapterId; text: string; href: string }`, `href` = first page of the chapter), each with the chapter number, title, one line, and a link.
4. **Overview video** (`id="overview"`): `SectionIntro` + `VideoEmbed youtubeId={getVideo(1)?.youtubeId ?? ''} title="What is FluxGate"`.
5. **Features**: the existing `features` grid.
6. **Screens**: `stage-editor`, `approvals`, `dashboards`, `features-list` as `ThemedImage` cards with captions, in a two-column grid.
7. **How it works**: `ArchitectureDiagram` + `architectureSteps` + link to `/architecture/`.
8. **For developers**: left: text and links to the developer guide and SDK reference; right: `<TerminalBlock title="Evaluate a flag over OFREP">` with a `<pre><code>` of the OFREP `curl` call (single-flag endpoint, `express-checkout`, context `targetingKey`, `country`, `user_tier`) followed by its JSON response, both copied from the verified examples in `reference/edge-api.mdx`.
9. **Performance and comparison**: two cards summarizing the existing previews, linking to `/performance/` and `/comparison/`.
10. **FAQ**: the existing three plus "How do I install FluxGate?" (answer: Docker Compose with the public images, five minutes, link text to the developer guide).
11. **CTA band**: "Run FluxGate in five minutes", the three commands from the developer guide sections 1–3 in a `TerminalBlock`, and a "Read the developer guide" button.

Update `src/site.ts` home meta: keep the title; set the description to the hero text; extend `faqSchema.mainEntity` with the new FAQ entries so JSON-LD and page match.

- [ ] **Step 1: Update the page test.** In `src/pages/pages.test.tsx` add:

```tsx
describe('home page sections', () => {
  const html = renderToString(<HomePage />)

  it('has the new hero and calls to action', () => {
    expect(html).toContain('Ship code anytime. Release features when they are ready.')
    expect(html).toContain('href="/docs/get-started/install/"')
    expect(html).toContain('href="#overview"')
  })

  it('links every numbered chapter', () => {
    for (const href of [
      '/docs/get-started/what-is-fluxgate/',
      '/docs/model-your-release/environments-and-pipelines/',
      '/docs/connect-your-app/clients-and-edge-server/',
      '/docs/ship-safely/approvals-and-policies/',
      '/docs/integrations/jira-setup/',
      '/docs/observe-and-operate/dashboards/',
    ]) {
      expect(html).toContain(`href="${href}"`)
    }
  })

  it('renders themed screenshots for both themes', () => {
    expect(html).toContain('/images/ui/system-overview-light.jpg')
    expect(html).toContain('/images/ui/system-overview-dark.jpg')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails.** `pnpm test src/pages` — expected FAIL on the hero text.
- [ ] **Step 3: Write `chapterCards` and `faqs` in `shared-content.ts`, then rewrite `HomePage.tsx`** with the sections above, using only the primitives, `Button`, `Card`, `Badge`, `ThemedImage`, `TerminalBlock`, and `VideoEmbed`.
- [ ] **Step 4: Run tests.** `pnpm test` — expected PASS.
- [ ] **Step 5: Build and review.** `pnpm build && pnpm preview`; check `/` at 1440 and 375 px in light and dark: no horizontal scroll, hero screenshot swaps with the theme, overview placeholder shows "Video coming soon".
- [ ] **Step 6: Commit** (`feat: product home page`).

---

# Phase 7 — Videos and release

### Task 24: YouTube video ids

Blocked until the user sends the 16 YouTube URLs. Do not start it before then.

**Files:** Modify `src/content/videos.ts`, `src/content/videos.test.ts`.

- [ ] **Step 1: Convert the URLs.** For each URL use `youtubeIdFromUrl` (Task 7) to get the 11-character id; set `youtubeId` and `uploadDate` (the publish date the user gives, or the date shown on the YouTube page, as `YYYY-MM-DD`).
- [ ] **Step 2: Add a completeness test** to `src/content/videos.test.ts`:

```ts
it('has a YouTube id and upload date for every video', () => {
  for (const [number, video] of Object.entries(videos)) {
    expect(video.youtubeId, `video ${number}`).toMatch(/^[\w-]{11}$/)
    expect(video.uploadDate, `video ${number}`).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  }
})
```

- [ ] **Step 3: Run tests and build.** `pnpm test && pnpm build`. Then `grep -c '"VideoObject"' dist/docs/model-your-release/targeting-rules/index.html` — expected `1`.
- [ ] **Step 4: Check playback.** In `pnpm preview`, open three docs pages and the home page; click play; the video plays from `youtube-nocookie.com`; before the click, the network log (`read_network_requests`) shows no request to `youtube-nocookie.com`.
- [ ] **Step 5: Commit** (`docs: link the demo videos on YouTube`).

### Task 25: Final verification and deploy check

**Files:** none expected; fix anything found in the file it belongs to.

- [ ] **Step 1: Full test and build.** `pnpm test && pnpm lint && pnpm build` — all pass.
- [ ] **Step 2: Visual pass.** With `pnpm preview` and the built-in browser, visit every route in `dist/sitemap.xml` at 1440 px and 375 px (`resize_window`), light and dark. For each: no horizontal scroll (`document.documentElement.scrollWidth <= window.innerWidth` via `javascript_tool`), no console errors (`read_console_messages`), images load.
- [ ] **Step 3: Search.** Search "targeting", "OFREP", and "encryption key"; each returns the expected page first or second.
- [ ] **Step 4: Lighthouse.** Run Lighthouse (chrome-devtools `lighthouse_audit`) on `/` and `/docs/model-your-release/targeting-rules/` against `pnpm preview`. Target 95 or more for Performance, Accessibility, and SEO. Fix and re-run until met, or report the remaining gap with its cause.
- [ ] **Step 5: Deployment readiness.** The deploy workflow runs on `aws-*` tags and is the user's decision. Do not push tags. Report to the user: the build is ready, the command they would run to deploy (`git tag aws-<date> && git push origin aws-<date>`), and the post-deploy checks to run: `curl -sI https://flux.forgeopslabs.com/docs/` (200, `text/html`), `curl -sI https://flux.forgeopslabs.com/pagefind/pagefind.js` (200), `curl -sI https://flux.forgeopslabs.com/downloads/docker-compose.demo.yml` (200), and a search in the live site.
- [ ] **Step 6: Push `main`** only if the user asks for it.
