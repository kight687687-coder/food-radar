# Ingredient Cleanup and AI Visuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean OCR-derived ingredient data, reduce the recognition card to the main ingredients, improve risk/persona text hierarchy, and make the AI completion intro visibly animated.

**Architecture:** Normalize OCR text in the Flask pipeline before classification and scoring, while keeping the original OCR text available only inside the pipeline. Keep the React result contract unchanged except for a bounded recognition presentation and richer stage text formatting. Use deterministic CSS motion for the intro overlay and respect reduced-motion preferences.

**Tech Stack:** Flask/Python, pytest, React, Vite, CSS animations.

## Global Constraints

- Do not let nutrition facts, percentages, units, marketing claims, or allergen notices count as ingredients.
- Recognition cards show at most 12 main ingredients.
- Risk tags use high/medium/low visual tones; audience reminders are plain dark text.
- AI judgment copy is concise and split into readable paragraphs.
- Intro animation must remain accessible with `prefers-reduced-motion`.

### Task 1: Normalize OCR Ingredients

**Files:**
- Modify: `backend/app.py` (`_parse_ingredients`)
- Test: `backend/tests/test_routes.py`

- [x] Add tests covering nutrition facts, threshold phrases, and concatenated ingredient text.
- [x] Run the focused tests and confirm they fail against the current parser.
- [x] Add deterministic filters and boundary splitting for nutrition/claim fragments.
- [x] Run the focused tests and the full backend suite.

### Task 2: Bound Recognition Presentation

**Files:**
- Modify: `web/src/utils/aiAnalysisStages.js`
- Modify: `web/src/components/AiAnalysisStages.jsx`
- Test: `web/tests/ai-analysis-stages.test.mjs`

- [x] Add a 12-item display limit while preserving the full result string for scoring/history.
- [x] Change the copy to distinguish main ingredients from additional recognized items.
- [x] Add unit coverage for deduplication/limit behavior.
- [x] Run web tests and lint.

### Task 3: Improve Findings and Judgment Readability

**Files:**
- Modify: `web/src/components/AiAnalysisStages.jsx`
- Modify: `web/src/styles/pages.css`
- Test: `web/tests/ai-analysis-stages.test.mjs`

- [x] Map risk levels to `danger`, `warning`, and `success` tags instead of one danger tone.
- [x] Render audience reminders as plain text rows.
- [x] Split judgment text on sentence boundaries and remove repetitive lead-ins.
- [x] Add focused assertions for the rendered structure and tone classes.

### Task 4: Strengthen AI Completion Intro Motion

**Files:**
- Modify: `web/src/styles/pages.css`
- Modify: `web/src/pages/ResultPage.jsx`
- Test: `web/tests/motion-parity.test.mjs`

- [x] Add a visible scan-ring/glow animation around the supplied image in the intro overlay.
- [x] Keep the image centered and use a static fallback under reduced motion.
- [x] Extend the intro timing without blocking the existing analysis sequence.
- [x] Run lint, tests, and production build.

### Task 5: Deploy and Verify

**Files:**
- Deploy: `web/`

- [x] Deploy the production build with `vercel deploy . --prod -y`.
- [x] Confirm the deployment reports `Ready` and includes `www.shianleida.cn` as an alias.
