# Food Radar Web Implementation Plan

> **For agentic workers:** Implement each checked task in order and keep `miniprogram/` and `backend/` unchanged.

**Goal:** Ship an independently buildable and Vercel-ready Web version of all Food Radar workflows.

**Architecture:** A React/Vite SPA uses React Router, local browser persistence, an isolated API adapter, reusable UI primitives, and page-level feature modules. Existing Flask contracts and product assets are reused.

**Tech Stack:** React 19, Vite 7, React Router 7, lucide-react, browser localStorage/IndexedDB, CSS.

## Global Constraints

- Preserve every original mini-program file.
- Implement all 17 routes without placeholder pages.
- Keep the existing Chinese copy, semantic palette, information hierarchy, and core flows.
- Support mobile widths from 375px and desktop widths through 1920px.
- Keep API keys and backend secrets out of client code.
- Pass `npm install`, `npm run build`, and `npm run preview`.

---

### Task 1: Application Foundation

**Files:** Create `web/package.json`, Vite config, environment example, Vercel config, entry files, shared styles, and copied assets/data.

- [ ] Configure scripts and SPA history fallback.
- [ ] Add global design tokens, accessibility states, mobile bottom navigation, and desktop navigation rail.
- [ ] Convert copied additive data to an ES module.

### Task 2: Browser Services And Shared State

**Files:** Create `web/src/services/*`, `web/src/context/AppContext.jsx`, `web/src/utils/*`, and reusable components.

- [ ] Implement guarded storage and family/history migrations.
- [ ] Implement backend requests with timeouts and normalized errors.
- [ ] Implement image reading and IndexedDB persistence.
- [ ] Implement toast, confirm dialog, loading, image, score, and layout primitives.

### Task 3: Primary Workflows

**Files:** Create pages for profile, home, scan, result, compare, history, report, toolbox, and mine.

- [ ] Preserve profile and guest onboarding.
- [ ] Port dashboard, scan upload, result interpretation, comparison, history, and report calculations.
- [ ] Implement complete loading, failure, empty, and retry states.

### Task 4: Supporting Workflows

**Files:** Create pages for avoid preferences, family management/editing, ingredient lookup, wiki/list detail, AI chat, and trend report.

- [ ] Preserve search, category filtering, member limits, active-member filtering, and local caches.
- [ ] Replace the unfinished report-card page with an actual trend summary.
- [ ] Keep AI features honest about backend availability and provide only clearly labeled deterministic fallback copy.

### Task 5: Verification And Deployment Handoff

**Files:** Create `web/README.md`; update this checklist as verification completes.

- [ ] Run dependency installation and production build.
- [ ] Start preview and exercise primary routes and interactions.
- [ ] Inspect 390px and 1440px screenshots and correct overflow or overlap.
- [ ] Document Vercel root, build command, output directory, environment, backend, and domain steps.
