# Food Radar API

This directory is an independent Flask API that can run locally or as a Vercel Python Function. The food scoring reference data comes from `data/csv`, so MySQL is not required for OCR analysis, scoring, comparison, AI chat, or encyclopedia requests.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python app.py
```

Run tests with:

```powershell
python -m pytest -v
```

Never commit `.env`. Add real provider credentials only to the local `.env` file or the Vercel project environment settings.

## Vercel project settings

- Framework Preset: Other
- Root Directory: `backend`
- Build Command: leave empty (Vercel installs `requirements.txt` automatically)
- Output Directory: leave empty
- Install Command: leave empty

Required environment variables:

- `BAIDU_OCR_API_KEY`
- `BAIDU_OCR_SECRET_KEY`
- `DEEPSEEK_API_KEY`
- `ALLOWED_ORIGINS` with the frontend Vercel URL and custom domains, separated by commas

Optional variables:

- `BAIDU_OCR_APP_ID` (not used by the current token flow)
- `DEEPSEEK_MODEL` (defaults to `deepseek-chat`)
- `DEEPSEEK_BASE_URL` (defaults to `https://api.deepseek.com`)
- `DATABASE_URL` for server-side scan history and wiki caching

When `DATABASE_URL` is not set, `/history` returns an empty compatible list and `/daily` returns an empty summary. The Web application keeps its own user data and scan history in browser storage.

After the backend is deployed, set the frontend Vercel project's `VITE_API_BASE_URL` to the backend HTTPS URL and redeploy the frontend.
