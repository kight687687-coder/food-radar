# Result Assistant Viewport Drag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the result-page AI nutritionist robot attached to the current viewport edge, allow bounded drag-and-snap positioning, and delay the prompt box until three seconds after page entry.

**Architecture:** Store the assistant's edge and cross-axis offset in `ResultPage`, derive fixed viewport coordinates from those values, and update them from pointer drag events. The robot remains visible immediately; a one-shot timer controls only the prompt box, and manual collapse disables future automatic reopening for the current result-page mount.

**Tech Stack:** React hooks, Pointer Events, CSS `position: fixed`, Node's built-in test runner, Vite.

## Global Constraints

- The robot must remain attached to one of the four viewport edges.
- Dragging must work with mouse and touch through Pointer Events.
- Releasing the robot must snap it to the nearest viewport edge.
- The prompt box appears once, three seconds after result-page entry, and never reopens after manual collapse during that page visit.
- Existing question generation, AI answering, and bottom answer sheet behavior remain unchanged.

### Task 1: Add pure viewport-position helpers

**Files:**
- Create: `web/src/utils/resultAssistantPosition.js`
- Test: `web/tests/result-assistant-position.test.mjs`

**Interfaces:**
- `clamp(value, min, max) -> number`
- `getAssistantPosition({ edge, offset, viewportWidth, viewportHeight, robotSize, margin }) -> { left, top }`
- `snapAssistantEdge({ left, top, viewportWidth, viewportHeight, robotSize }) -> { edge, offset }`

- [ ] **Step 1: Write failing tests** for left/right/top/bottom coordinate derivation, bounded offsets, nearest-edge snapping, and tiny viewports.
- [ ] **Step 2: Run** `node --test tests/result-assistant-position.test.mjs` and confirm the helper module is missing.
- [ ] **Step 3: Implement** deterministic geometry helpers with no DOM dependencies so tests can run in Node.
- [ ] **Step 4: Run** the focused test again and confirm all cases pass.

### Task 2: Add viewport drag state and delayed prompt behavior

**Files:**
- Modify: `web/src/pages/ResultPage.jsx`
- Modify: `web/src/styles/pages.css`

**Interfaces:**
- `ResultAssistant` accepts `promptVisible`, `onPromptDismiss`, and `onPositionChange` props.
- Pointer handlers emit the next `{ edge, offset }` position and call `setPointerCapture`/`releasePointerCapture` when available.

- [ ] **Step 1: Add a three-second one-shot timer** that sets prompt visibility without delaying robot rendering; clear it on unmount.
- [ ] **Step 2: Add a `promptDismissed` state** so clicking the existing collapse control prevents automatic reopening for the current page visit.
- [ ] **Step 3: Add drag state** with the robot's starting rectangle and pointer coordinates; update only the cross-axis offset while dragging.
- [ ] **Step 4: Snap on pointer release** using the pure helper, then update fixed coordinates from the selected edge and offset.
- [ ] **Step 5: Change assistant positioning CSS** from result-page-relative placement to viewport-fixed placement, preserve mobile safe-area spacing, and add a dragging cursor/state.
- [ ] **Step 6: Keep the prompt box width bounded** so it cannot cover the result score or analysis cards on narrow screens.

### Task 3: Verify interaction and regression coverage

**Files:**
- Modify: `web/tests/ai-analysis-stages.test.mjs` only if shared assertions need extension.
- Test: `web/tests/result-assistant-position.test.mjs`

- [ ] **Step 1: Run** `node --test tests/result-assistant-position.test.mjs tests/ai-analysis-stages.test.mjs tests/motion-parity.test.mjs`.
- [ ] **Step 2: Run** `npm run lint` from `web`.
- [ ] **Step 3: Run** `npm run build` from `web`.
- [ ] **Step 4: Use the local result page to verify** immediate robot visibility, delayed prompt appearance, collapse persistence, dragging on desktop/mobile-sized viewport, edge snapping, scrolling, question selection, and answer-sheet closing.
- [ ] **Step 5: Run** `git diff --check` and inspect the final diff for unrelated changes.

