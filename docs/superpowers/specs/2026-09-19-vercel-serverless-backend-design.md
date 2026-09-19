# Food Radar Vercel Serverless Backend Design

## Goal

Move the existing Flask food-analysis backend from the expired VPS to a separate Vercel Serverless API while preserving the current request and response contracts used by both the Web client and the native WeChat mini-program.

## Approved Approach

The first production-capable version is stateless by default. Food safety reference data is loaded from the existing CSV files packaged with the function, Web scan history remains in browser storage, and database-backed history and AI cache behavior become optional rather than startup requirements. This lets OCR, scoring, comparison, wiki queries, and AI chat work without buying a server or provisioning a database first.

## Deployment Boundary

- The frontend remains a Vite project deployed from `web/`.
- The backend is deployed as a separate Vercel project rooted at `backend/`.
- `backend/api/index.py` exports the existing Flask application for Vercel.
- `backend/vercel.json` routes API requests to the Flask function and defines the Python runtime configuration.
- The expired VPS deployment script and systemd service are retained only as legacy files; they are not used by Vercel.

## API Compatibility

The following routes keep their existing paths and response envelope where one already exists:

- `GET /health`
- `POST /analyze`
- `POST /compare`
- `GET /history`
- `GET /daily`
- `POST /api/ai-compare`
- `POST /api/ai-suggestion`
- `POST /api/ai-chat`
- `POST /api/wiki-query`

`/analyze`, `/compare`, and the AI routes remain fully functional without a database. When no database is configured, `/history` returns an empty list and `/daily` returns an empty daily summary instead of failing. The Web application continues to use its local browser history. A future cloud database can be enabled without changing frontend routes.

## Reference Data

The scoring engine loads these packaged files once per warm function instance:

- `data/csv/additives.csv`
- `data/csv/group_warnings.csv`
- `data/csv/avoid_options.csv`
- `data/csv/beneficial_ingredients.csv`

The loader exposes plain Python records to the scoring module. SQLAlchemy is removed from the mandatory analysis path. The existing trained classifier remains available when its dependencies load successfully, while keyword classification remains the fallback so a model-loading problem cannot make OCR analysis unavailable.

## OCR Integration

The Baidu OCR client reads credentials only from environment variables, validates configuration before making a request, caches access tokens in memory during a warm invocation, applies explicit connect/read timeouts, and maps provider errors to safe user-facing messages. Image Base64 content and the full provider response are never logged.

Required variables:

- `BAIDU_OCR_API_KEY`
- `BAIDU_OCR_SECRET_KEY`

`BAIDU_OCR_APP_ID` is optional because the current REST token flow does not use it.

## DeepSeek Integration

DeepSeek is configured only through server-side environment variables:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`, default `deepseek-chat`
- `DEEPSEEK_BASE_URL`, default `https://api.deepseek.com`

AI client creation is lazy so importing the Flask app does not fail when the key is absent. OCR analysis still returns deterministic scoring and a locally generated summary if DeepSeek is unavailable or times out. Dedicated AI endpoints return a clear configuration or upstream-service error rather than exposing provider details or secrets.

## Optional Database

`DATABASE_URL` is optional. When configured with a supported SQLAlchemy URL, scan history and wiki cache persistence can be enabled. When absent, application startup and all core analysis routes continue normally. No local SQLite writes are relied on because Vercel function filesystems are ephemeral.

## Security And Limits

- No credential is committed to Git, copied into the frontend, or embedded in Vercel configuration files.
- `.env` remains ignored; `.env.example` contains names and documentation only.
- Requests validate JSON shape and reject missing or oversized images before calling paid providers.
- Provider exception text is logged in redacted form and is not returned verbatim to clients.
- CORS accepts configured frontend origins plus local development origins; credentials are not enabled.
- Existing credentials disclosed in chat should be rotated before the production deployment.

## Error Handling

- Configuration errors use a distinct API error code and an actionable Chinese message.
- Invalid images and OCR failures return HTTP-compatible application errors without a stack trace.
- Database failures never make stateless analysis fail; persistence is best-effort.
- DeepSeek failures degrade `/analyze` to a deterministic report.
- The global Flask error handler preserves the existing `{code, msg, data}` response shape.

## Testing

- Unit tests cover CSV loading, additive matching, avoid matching, deterministic scoring, missing credentials, provider failures, and deterministic AI fallback.
- Flask route tests mock Baidu OCR and DeepSeek and verify response compatibility.
- Import smoke tests verify the application starts with no database and no secrets.
- Local checks run `pytest` and import the Vercel entrypoint.
- Deployment checks call only the non-secret `/health` endpoint after a preview deployment; paid OCR and AI calls are tested after environment variables are configured by the user in Vercel.

## Frontend Connection

After the backend preview is deployed, the frontend Vercel project receives:

```text
VITE_API_BASE_URL=https://<backend-project>.vercel.app
```

The frontend is then redeployed so scan, comparison, wiki AI fallback, and AI nutritionist requests use the new HTTPS endpoint.

