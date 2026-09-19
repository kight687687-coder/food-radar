# Food Radar Web Motion Parity Implementation Plan

> **For agentic workers:** Execute inline in the existing workspace. Preserve the mini-program source and reproduce only motion already present in its WXSS. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the native mini-program's scan animation, page entrances, tab feedback, card staging, and overlay transitions in the Web client.

**Architecture:** Keep motion dependency-free. React supplies route and element structure, while `global.css` owns shared route/tab/overlay motion and `pages.css` owns scan and home-page keyframes. A Node built-in test verifies the required motion contract before lint and Vite build checks.

**Tech Stack:** React, React Router, CSS keyframes/transitions, Node.js built-in test runner, Vite, ESLint.

## Global Constraints

- Do not modify `miniprogram/`.
- Do not replace or redesign existing Web image assets, text, layout, or business flows.
- Match the timing and movement already defined by the mini-program WXSS.
- Use opacity and transforms for animation where practical.
- Respect `prefers-reduced-motion: reduce`.
- Keep desktop motion restrained and prioritize mobile parity at 375px, 390px, and 414px.

---

### Task 1: Add a Web motion parity contract test

**Files:**
- Create: `web/tests/motion-parity.test.mjs`
- Modify: `web/package.json`

**Interfaces:**
- Consumes: `web/src/components/AppShell.jsx`, `web/src/pages/ScanPage.jsx`, `web/src/styles/global.css`, and `web/src/styles/pages.css` as UTF-8 text.
- Produces: `npm run test:motion`, which fails when required scan, route, tab, overlay, home, or reduced-motion hooks are absent.

- [ ] **Step 1: Write the failing Node test**

Create assertions using `node:test`, `node:assert/strict`, and `fs.readFileSync` for these exact contracts:

```js
assert.match(scanPage, /scan-frame/)
assert.match(scanPage, /scan-line/)
assert.match(scanPage, /scan-corner lt/)
assert.match(appShell, /route-stage/)
assert.match(globalCss, /@keyframes routeEnter/)
assert.match(globalCss, /@keyframes scanTabPop/)
assert.match(globalCss, /@keyframes overlayFadeIn/)
assert.match(globalCss, /@keyframes panelSlideIn/)
assert.match(pagesCss, /@keyframes scanSweep/)
assert.match(pagesCss, /@keyframes cardRise/)
assert.match(pagesCss, /@keyframes scorePop/)
assert.match(globalCss, /prefers-reduced-motion: reduce/)
```

Add this script to `web/package.json`:

```json
"test:motion": "node --test tests/motion-parity.test.mjs"
```

- [ ] **Step 2: Run the test and verify it fails before implementation**

Run: `npm --prefix web run test:motion`

Expected: FAIL because `scan-frame`, `route-stage`, and the new keyframes are not yet present.

### Task 2: Restore the native scan illustration and looping sweep

**Files:**
- Modify: `web/src/pages/ScanPage.jsx`
- Modify: `web/src/styles/pages.css`
- Test: `web/tests/motion-parity.test.mjs`

**Interfaces:**
- Produces: `.scan-frame`, `.scan-line`, and four `.scan-corner` elements inside `.label-paper`.
- Produces: `scanHeroIn` and `scanSweep` keyframes using the original 0.34-second entrance and 2.2-second looping sweep.

- [ ] **Step 1: Replace the static scan approximation with the native structure**

The illustration must contain this shape while preserving the existing `AI` and `配料表` chips:

```jsx
<div className="scan-frame">
  <span className="scan-line" />
  <i className="scan-corner lt" />
  <i className="scan-corner rt" />
  <i className="scan-corner lb" />
  <i className="scan-corner rb" />
</div>
```

- [ ] **Step 2: Port the original scan timing and geometry**

Add `animation: scanHeroIn .34s ease-out both` to `.scan-hero`. Style the corners with green top/side borders and use:

```css
.scan-line { animation: scanSweep 2.2s ease-in-out infinite; }
@keyframes scanSweep {
  0% { transform: translateY(0); opacity: 0; }
  12% { opacity: 1; }
  50% { transform: translateY(var(--scan-distance)); opacity: 1; }
  88% { opacity: 1; }
  100% { transform: translateY(0); opacity: 0; }
}
```

Define `--scan-distance` for desktop and mobile scan-frame heights so the line remains inside the frame.

- [ ] **Step 3: Run the motion contract test**

Run: `npm --prefix web run test:motion`

Expected: scan assertions pass; shared route/tab/overlay assertions still fail until Task 3.

### Task 3: Restore route, home, tab, overlay, and press motion

**Files:**
- Modify: `web/src/components/AppShell.jsx`
- Modify: `web/src/styles/global.css`
- Modify: `web/src/styles/pages.css`
- Test: `web/tests/motion-parity.test.mjs`

**Interfaces:**
- Produces: a `.route-stage` keyed by `location.pathname` so page-entry animation restarts on route changes.
- Produces: shared `routeEnter`, `scanTabPop`, `overlayFadeIn`, `dialogPopIn`, and `panelSlideIn` keyframes.

- [ ] **Step 1: Key the route content without delaying navigation**

Wrap the outlet as follows:

```jsx
<main className="app-main">
  <div className="route-stage" key={location.pathname}>
    <Outlet />
  </div>
</main>
```

- [ ] **Step 2: Add restrained shared transitions**

Use the original motion scale:

```css
.route-stage { animation: routeEnter .28s ease-out both; }
.tab-link, .tab-icon, .tab-icon img { transition: transform .18s ease, opacity .18s ease, color .18s ease; }
.tab-link.active .tab-icon img { transform: scale(1.05); }
.tab-primary.active .tab-icon { animation: scanTabPop .26s ease-out; }
.sheet-backdrop, .dialog-backdrop, .loading-overlay { animation: overlayFadeIn .28s ease both; }
.bottom-sheet { animation: panelSlideIn .36s cubic-bezier(.22, 1, .36, 1) both; }
.dialog, .result-avoid-modal, .loading-panel { animation: dialogPopIn .24s ease-out both; }
```

Ensure press states use the mini-program scale values: normal tabs `0.94`, central scan tab `translateY(-6px) scale(0.96)`, and interactive cards approximately `0.98`.

- [ ] **Step 3: Stage the home page like the original WXSS**

Apply `cardRise .34s`, `softPop .32s .08s`, `scorePop .36s .05s`, and later `cardRise` delays to the existing home hero, score ring, quick grid, and recent section. Use selectors scoped to `.home-page` so other pages do not inherit the stagger.

- [ ] **Step 4: Complete reduced-motion behavior**

Inside the existing reduced-motion media query, stop the infinite scan loop and force animated elements visible at their final transform:

```css
.scan-line { animation: none !important; opacity: .7; transform: translateY(50%); }
.route-stage, .scan-hero, .home-page .section, .home-score-ring { opacity: 1 !important; transform: none !important; }
```

- [ ] **Step 5: Run the motion contract test**

Run: `npm --prefix web run test:motion`

Expected: PASS.

### Task 4: Verify, commit, and deploy the motion pass

**Files:**
- Modify only if verification exposes defects in the files above.

**Interfaces:**
- Produces: a Vercel Preview URL containing the motion parity changes.

- [ ] **Step 1: Run automated verification**

Run:

```powershell
npm --prefix web run test:motion
npm --prefix web run lint
npm run build
```

Expected: all commands exit successfully.

- [ ] **Step 2: Run local preview startup verification**

Run `npm run preview`, confirm Vite reports `http://localhost:4173/`, then stop the process.

- [ ] **Step 3: Check repository safety**

Run `git diff --check` and `git status --short`. Confirm there are no changes under `miniprogram/` and no generated `dist`, `.vercel`, or credential files staged.

- [ ] **Step 4: Commit the motion implementation**

```powershell
git add web/src/components/AppShell.jsx web/src/pages/ScanPage.jsx web/src/styles/global.css web/src/styles/pages.css web/tests/motion-parity.test.mjs web/package.json web/package-lock.json
git commit -m "feat: restore mini-program motion in web app"
```

- [ ] **Step 5: Create a Vercel Preview deployment**

Run from `web/`: `vercel deploy . -y --target preview --force`

Expected: Vercel reports a `READY` Preview URL. Do not promote it to production.
