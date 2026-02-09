# LazyDatabricks Marketing Website Requirements

**Domain:** lazydatabricks.com
**Stack:** Next.js 14+ (App Router), Fumadocs, Tailwind CSS
**Purpose:** Marketing site + documentation for LazyDatabricks TUI

---

## 1. Project Overview

LazyDatabricks is a terminal UI (TUI) for Databricks that provides keyboard-driven management of clusters, jobs, pipelines, warehouses, and billing. The website needs to:

1. **Market** the tool to Databricks users (platform engineers, data engineers, MLOps)
2. **Document** installation, configuration, and usage
3. **Showcase** features with visuals (terminal recordings, screenshots)

---

## 2. Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14+ (App Router) |
| Docs | Fumadocs |
| Styling | Tailwind CSS |
| Animations | Framer Motion (optional) |
| Terminal Demos | asciinema embeds or SVG recordings |
| Hosting | Vercel |
| Analytics | Vercel Analytics or Plausible |

---

## 3. Site Structure

```
/                       # Landing page (hero, features, CTA)
/docs                   # Documentation home
/docs/getting-started   # Installation & setup
/docs/configuration     # Config file, profiles, extensions
/docs/screens           # Screen-by-screen guide
  /docs/screens/home
  /docs/screens/clusters
  /docs/screens/jobs
  /docs/screens/pipelines
  /docs/screens/warehouses
  /docs/screens/billing
/docs/extensions        # Extension system
/docs/keybindings       # Full keybinding reference
/changelog              # Release notes
```

---

## 4. Page Requirements

### 4.1 Landing Page (`/`)

**Hero Section:**
- Tagline: "The Lazy Way to Manage Databricks" or similar
- Subtitle: "A keyboard-driven TUI for clusters, jobs, pipelines & billing"
- Terminal animation showing LazyDatabricks in action (asciinema or animated SVG)
- Primary CTA: "Get Started" → `/docs/getting-started`
- Secondary CTA: "View on GitHub" → repo link

**Features Section:**
- 6 feature cards with icons:
  1. **Clusters** - Start, stop, resize with a keystroke
  2. **Jobs** - Browse runs, view logs, trigger manually
  3. **Pipelines** - DLT pipeline management and updates
  4. **Warehouses** - SQL warehouse control
  5. **Billing** - DBU cost visibility by SKU and resource
  6. **Armed Mode** - Safety guard for destructive actions

**Why LazyDatabricks Section:**
- Speed comparison (TUI vs. clicking through UI)
- Works over SSH / in containers
- No browser required
- Profile switching for multi-workspace

**Installation Snippet:**
```bash
pip install lazydatabricks
lazydatabricks
```

**Footer:**
- GitHub link
- License (MIT or Apache 2.0)
- "Built for Databricks users, by Databricks users"

---

### 4.2 Documentation (`/docs`)

Use Fumadocs for:
- MDX content with syntax highlighting
- Sidebar navigation (auto-generated from file structure)
- Search (Fumadocs built-in or Algolia)
- Dark/light mode toggle
- Copy buttons on code blocks

**Doc Pages:**

| Page | Content |
|------|---------|
| Getting Started | pip install, first launch, auth setup |
| Configuration | `~/.lazydatabricks/config.toml`, profiles, themes |
| Clusters | Screen walkthrough, keybindings, armed actions |
| Jobs | Three-pane layout, run history, logs |
| Pipelines | DLT updates, full refresh, stop |
| Warehouses | Start/stop/resize |
| Billing | Extension setup, SKU costs, breakdown |
| Extensions | How extensions work, creating custom |
| Keybindings | Complete reference table |
| Themes | Built-in themes, custom CSS |

---

### 4.3 Changelog (`/changelog`)

- Semantic versioning
- Grouped by version with dates
- Categories: Added, Changed, Fixed, Removed

---

## 5. Design Requirements

### 5.1 Visual Identity

| Element | Specification |
|---------|---------------|
| Primary Color | `#e94560` (LazyDatabricks red) |
| Background | Dark theme default (`#0f0f0f` or similar) |
| Font (headings) | JetBrains Mono or similar monospace |
| Font (body) | Inter or system fonts |
| Terminal styling | Match LazyDatabricks TUI aesthetic |

### 5.2 Components

- **Terminal Window Component**: Styled container for code/terminal content
- **Keybinding Badge**: `<kbd>` styled badges for keys (e.g., `[A]` `[r]`)
- **Feature Card**: Icon + title + description
- **Callout/Admonition**: Info, warning, tip boxes for docs

### 5.3 Responsive

- Mobile-friendly landing page
- Docs sidebar collapses to hamburger on mobile
- Terminal demos scale or show static fallback

---

## 6. Content Requirements

### 6.1 Terminal Recordings

Create asciinema recordings for:
1. First launch and home screen
2. Cluster start/stop flow
3. Jobs → Runs → Logs drill-down
4. Billing extension walkthrough
5. Armed mode activation

**Specs:**
- 80x24 terminal size
- Dark theme matching site
- 1.5x-2x playback speed for demos

### 6.2 Screenshots

- Each screen (Home, Clusters, Jobs, Pipelines, Warehouses, Billing)
- Armed mode indicator
- Help overlay

### 6.3 Copy

- Keep it concise and technical
- Target audience: experienced Databricks users
- Avoid marketing fluff, focus on utility

---

## 7. Technical Requirements

### 7.1 Fumadocs Setup

```bash
npx create-fumadocs-app@latest lazydatabricks
```

Configure:
- `fumadocs.config.ts` for docs structure
- MDX components for custom elements
- Syntax highlighting theme (match TUI colors)

### 7.2 SEO

- Meta titles/descriptions for all pages
- Open Graph images (auto-generated or custom)
- Sitemap generation
- robots.txt

### 7.3 Performance

- Static generation for all pages
- Lazy-load terminal embeds
- Image optimization via Next.js
- Core Web Vitals targets: LCP < 2.5s, CLS < 0.1

### 7.4 Deployment

- Vercel (automatic from GitHub)
- Custom domain: lazydatabricks.com
- Preview deployments for PRs

---

## 8. Future Considerations

- **Blog**: Release announcements, tips & tricks
- **Discord/Community**: Link to community channel
- **Sponsors**: If open source, sponsor recognition
- **Video Tutorials**: YouTube embeds for complex workflows

---

## 9. Milestones

| Phase | Deliverables |
|-------|--------------|
| 1. Foundation | Next.js + Fumadocs setup, landing page, basic docs structure |
| 2. Content | All doc pages written, terminal recordings created |
| 3. Polish | Design refinements, SEO, analytics |
| 4. Launch | Domain configured, go live |

---

## 10. Reference

- [Fumadocs](https://fumadocs.vercel.app/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Tailwind CSS](https://tailwindcss.com/)
- [asciinema](https://asciinema.org/)
