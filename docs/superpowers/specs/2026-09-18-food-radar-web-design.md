# Food Radar Web Migration Design

## Goal

Create a production-ready browser version of Food Radar while preserving the native WeChat mini-program and its product structure, copy, visual language, workflows, and backend contract.

## Architecture

The Web client lives under `web/` as an independent React and Vite single-page application. React Router replaces WeChat navigation, a small application context owns profile/family/history state, browser storage replaces synchronous WeChat storage, and a dedicated API module preserves the Flask response contract.

The original `miniprogram/` and `backend/` directories remain untouched. Shared visual assets and the additive encyclopedia dataset are copied into the Web application so that Web builds do not depend on WeChat path resolution or CommonJS runtime behavior.

## Pages

All 17 mini-program pages receive browser routes. The five tab pages remain primary navigation destinations. Secondary pages use a consistent back action and remain directly addressable so browser refresh and Vercel history fallback work correctly.

The mini-program's unfinished card report is replaced by a working local trend report using persisted scan history. This is the only intentional functional expansion, required to avoid shipping a placeholder route.

## Platform Adaptation

- `wx.request` becomes `fetch` behind `src/services/api.js`.
- `wx.getStorageSync` and `wx.setStorageSync` become guarded JSON `localStorage` helpers.
- Scan images use FileReader for upload and IndexedDB for durable local blobs.
- Navigation uses React Router.
- Toast, modal, loading, and empty states are native React UI.
- Image picking uses accessible file inputs with `accept="image/*"`.
- WeChat login is not fabricated; the existing product already uses a local guest profile and timestamp user id, which is preserved.
- No location, map, payment, subscription, cloud development, or WeChat OAuth code exists in the source.

## Backend And Environment

`VITE_API_BASE_URL` configures the existing Flask API. Production requires an HTTPS backend origin because the current hard-coded HTTP IP would be blocked as mixed content on a Vercel HTTPS site. Missing configuration produces actionable UI errors while local history, profiles, reports, search, and encyclopedia data remain usable.

## Responsive Design

Mobile keeps the mini-program's single-column hierarchy and bottom tab bar. Desktop uses a restrained left navigation rail and a bounded content canvas, with two-column layouts only where the original information hierarchy benefits from the additional width. Existing semantic colors, spacing, cards, typography, assets, loading states, and dialogs remain recognizable.

## Verification

The Web project must pass dependency installation, production build, route smoke checks, and responsive visual inspection at 390px and 1440px widths. Direct child-route requests are handled by `web/vercel.json`.
