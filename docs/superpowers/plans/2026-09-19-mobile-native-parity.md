# Food Radar Mobile Native-Parity Implementation Plan

> **For agentic workers:** Execute inline in the existing workspace and preserve `miniprogram/` and `backend/`.

**Goal:** Reproduce the native mini-program's mobile hierarchy, spacing, and icon system in the React Web client.

**Architecture:** Add a reusable original-iconfont component and a mobile-first parity layer. Adjust React markup only where Web currently has extra or differently grouped elements that CSS cannot faithfully correct.

**Tech Stack:** React, Vite, React Router, CSS, bundled FoodRadarIconfont, original PNG assets.

## Global Constraints

- The mini-program WXML/WXSS is the visual source of truth.
- Mobile parity applies from 320px through 899px.
- Desktop behavior remains available at 900px and above.
- Original images and glyphs replace generic feature icons.
- `npm run lint` and `npm run build` must pass.

---

### Task 1: Restore the original icon system

**Files:** Create `web/src/components/OriginalIcon.jsx`; modify `web/src/styles/global.css` and mobile navigation/page components.

- [ ] Define all glyph mappings present in `miniprogram/app.wxss`.
- [ ] Use original tab glyphs and scan action image in the mobile tab bar.
- [ ] Replace branded Lucide and feature-PNG usages with the exact glyph or image used by the corresponding WXML.

### Task 2: Match the five tab pages

**Files:** Modify `HomePage.jsx`, `ScanPage.jsx`, `ReportPage.jsx`, `ToolboxPage.jsx`, `MinePage.jsx`, `global.css`, and `pages.css`.

- [ ] Match mobile hierarchy and remove Web-only structural differences.
- [ ] Convert original rpx measurements to the 375px baseline.
- [ ] Preserve all working React interactions and browser storage behavior.

### Task 3: Match supporting pages

**Files:** Modify profile, result, compare, history, family, avoid, ingredient, wiki, chat, and trend components and styles.

- [ ] Remove feature graphics absent from original WXML.
- [ ] Restore original list, form, empty-state, modal, and detail-card grouping.
- [ ] Retain honest backend unavailable states.

### Task 4: Verify mobile parity

**Files:** Build output only.

- [ ] Run lint and build.
- [ ] Render 375px, 390px, and 414px screenshots for the five tab routes.
- [ ] Verify no horizontal overflow and no missing image/font resources.
- [ ] Smoke-test all 17 routes and create a new Vercel preview deployment.
