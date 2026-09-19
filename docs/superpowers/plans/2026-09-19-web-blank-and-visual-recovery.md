# Food Radar Web Blank-Screen And Visual Recovery Implementation Plan

> **For agentic workers:** Execute inline in the existing workspace. Do not modify `miniprogram/` or `backend/`.

**Goal:** Repair the empty post-onboarding route and visually align the Web client with the existing mini-program assets.

**Architecture:** Keep the React/Vite SPA and current routes. Fix the route boundary at the application entry, add a React error boundary, and centralize original image mappings so primary navigation and feature cards consistently use repository assets.

**Tech Stack:** React, Vite, React Router, CSS, browser localStorage/IndexedDB.

## Global Constraints

- Preserve all original mini-program and backend files.
- Use original PNG resources for branded navigation and core feature imagery.
- Keep Lucide only for universal interface controls without a supplied branded asset.
- Keep mobile and desktop navigation usable and accessible.
- Pass `npm run lint` and `npm run build`.

---

### Task 1: Repair rendering boundaries

**Files:** Modify `web/src/main.jsx`; create `web/src/components/AppErrorBoundary.jsx`.

- [ ] Change the nested profile guard to render React Router's `Outlet` when a profile exists.
- [ ] Wrap the app in an error boundary with a reload and clear-local-data recovery path.
- [ ] Verify first-run `/profile`, returning-user `/`, and direct `/scan` rendering.

### Task 2: Restore original navigation assets

**Files:** Modify `web/src/components/AppShell.jsx`, `web/src/styles/global.css`.

- [ ] Map every tab to inactive and active PNG paths from `web/public/images/tabbar`.
- [ ] Use the original 3D scan action image for the featured center tab.
- [ ] Adapt the same assets to the desktop rail without changing route behavior.

### Task 3: Restore feature imagery

**Files:** Modify relevant files under `web/src/pages/` and `web/src/styles/pages.css`.

- [ ] Replace scan capability line icons with score, risk, family, avoid, benefit, and AI feature images.
- [ ] Restore the eight original exploration service images and AI nutritionist avatar.
- [ ] Restore original images for profile/report/result cards where the repository contains an exact semantic match.

### Task 4: Verify and redeploy

**Files:** Production build output only.

- [ ] Run lint and production build.
- [ ] Run a local preview and capture 390px and 1440px screenshots for `/`, `/scan`, and `/toolbox`.
- [ ] Check direct child-route refresh behavior.
- [ ] Create a new Vercel preview deployment and report its URL; do not replace production until the preview is verified.
