# 快速体验中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `/examples` into a compact quick experience center with a stable local PK demo and links to AI nutritionist and additive encyclopedia.

**Architecture:** Keep the existing example food data and comparison computation. Add a small preset builder that combines two local example results, let `ExamplesPage` seed the existing compare preset, and add presentation-only sections for the three experiences. The existing `/compare` page consumes and clears the preset without changing real upload behavior.

**Tech Stack:** React, React Router, existing local storage helpers, existing CSS in `web/src/styles/pages.css`, Vitest/browser test scripts already configured in `web`.

## Global Constraints

- Preserve the existing Web visual style and motion transitions.
- Use local fixed results for the PK demo; do not call OCR, AI, or add history records.
- Keep the actual upload entry available.
- Keep mobile images fully visible and text within its parent.

---

### Task 1: Add a reusable local PK preset

**Files:**
- Modify: `web/src/data/exampleFoods.js`
- Modify: `web/src/services/storage.js` only if the existing preset helper needs no changes after inspection
- Test: existing web test suite

**Interfaces:**
- Produces `getExampleComparisonPreset(foodAId, foodBId)` returning `{ foodA, foodB }` with each result containing `imageSrc` and `exampleId`.

- [ ] **Step 1: Implement the preset helper**

Use the existing `getExampleFood` lookup, clone each result, and keep image paths on the result so `ComparePage` can render the sample images without saving them to IndexedDB.

- [ ] **Step 2: Run lint/build**

Run `npm run lint` and `npm run build` from `web`. Expected: both commands pass.

### Task 2: Expand the quick experience page

**Files:**
- Modify: `web/src/pages/ExamplesPage.jsx`
- Modify: `web/src/styles/pages.css`

**Interfaces:**
- `ExamplesPage` calls `setComparePreset(getExampleComparisonPreset('xiaokaochang', 'ice-black-tea'))` and navigates to `/compare`.
- New UI entry classes are scoped under `.examples-page`.

- [ ] **Step 1: Add PK demo section**

Render two real example images, labels, a short description, and a clear action button. Keep the section compact and make the whole card clickable.

- [ ] **Step 2: Add AI nutritionist and encyclopedia entries**

Render two small action cards linking to `/ai-chat` and `/wiki`. Use copy that is useful to ordinary users, including `150+ 种添加剂百科` only as an entry label.

- [ ] **Step 3: Add responsive styling**

Use a two-column tool grid on desktop and one column on mobile. Use fixed image dimensions/aspect ratios and `object-fit: contain` for sample product photos.

- [ ] **Step 4: Run focused verification**

Run `npm run lint`, `npm run build`, and the existing test command from `web`. Expected: all pass with no new warnings.

### Task 3: Verify routing and deployed behavior

**Files:**
- Modify: none unless verification finds a regression

- [ ] **Step 1: Start the local web server**

Run the existing development command from `web` and open `/examples` in a browser.

- [ ] **Step 2: Verify interactions**

Check all three single-food examples, the PK entry, the AI nutritionist entry, the encyclopedia entry, and the upload entry on desktop and mobile widths.

- [ ] **Step 3: Deploy the Web app**

Run the repository's existing production deployment command and confirm `/examples` and `/compare` are available on `www.shianleida.cn`.
