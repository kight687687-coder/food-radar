# Food Radar Web

Independent React/Vite migration of the native WeChat mini-program. The original `../miniprogram` and `../backend` directories are intentionally preserved.

## Commands

```bash
npm install
npm run dev
npm run build
npm run preview
```

Run commands from `web/`.

Do not open `index.html` or `dist/index.html` with a `file://` URL. Vite applications require an HTTP server. On Windows, you can double-click `../启动Web版.bat` instead.

## Configuration

Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` to an HTTPS deployment of the existing Flask backend. The browser version keeps profiles, family members, scan history, encyclopedia caches, and selected images in browser storage. AI analysis, OCR recognition, comparison analysis, and remote wiki misses require the backend.

## Vercel

Use `web` as Root Directory, `npm run build` as Build Command, and `dist` as Output Directory. `vercel.json` rewrites direct child routes to `index.html`. Add `VITE_API_BASE_URL` in the Vercel project environment variables.
