# Food Radar Vercel Serverless Backend Implementation Plan

> **For agentic workers:** Execute inline in the existing workspace. Preserve the native mini-program and Web API contracts, and never place real credentials in files or command output.

**Goal:** Make the existing Flask OCR, food scoring, comparison, wiki, and AI chat APIs deployable as a separate Vercel Serverless project without requiring a database.

**Architecture:** Package the Flask app behind `backend/api/index.py`, replace the mandatory SQL scoring path with a cached CSV repository, make persistence optional, and create provider clients lazily from server-side environment variables. Preserve all current route paths and the `{code, msg, data}` response envelope used by the clients.

**Tech Stack:** Python 3, Flask, Flask-CORS, requests, OpenAI Python SDK, optional SQLAlchemy, pytest, Vercel Python Functions.

## Global Constraints

- Never write the user-provided Baidu or DeepSeek values into the repository.
- Keep `miniprogram/` and `web/` behavior compatible with existing endpoint paths.
- Core analysis must start and run without `DATABASE_URL`.
- OCR image Base64 and full provider responses must never be logged.
- Provider failures must return safe Chinese messages and must not expose credentials.
- `pytest` and a production import smoke test must pass before deployment.

---

### Task 1: Add tests for stateless startup and CSV scoring

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_data_store.py`
- Create: `backend/tests/test_score.py`
- Create: `backend/requirements-dev.txt`

**Interfaces:**
- Consumes: existing CSV files under `backend/data/csv/`.
- Produces: executable expectations for `load_reference_data()` and `score_ingredients()`.

- [ ] Add a fixture that clears credential and database environment variables before importing backend modules.
- [ ] Add a test asserting the CSV repository returns non-empty additives, warnings, avoid options, and beneficial ingredients.
- [ ] Add a test asserting a known high-risk additive reduces the score and appears in `risk_additives`.
- [ ] Add a test asserting an empty optional database configuration does not affect scoring.
- [ ] Run `pytest backend/tests/test_data_store.py backend/tests/test_score.py -v` and confirm the tests fail before implementation.

### Task 2: Replace mandatory scoring database reads with cached CSV data

**Files:**
- Create: `backend/data_store.py`
- Modify: `backend/score.py`

**Interfaces:**
- Produces: `load_reference_data(force_reload=False) -> ReferenceData`.
- Produces: `score_ingredients(ingredients_list, group_type=None, user_options=None, avoid_ids=None) -> dict` with the existing response keys.

- [ ] Implement immutable record dataclasses for additives, group warnings, avoid options, and beneficial ingredients.
- [ ] Parse slash- or comma-separated aliases and keywords consistently.
- [ ] Cache the loaded CSV data with `functools.lru_cache`.
- [ ] Refactor matching and score calculation to use records instead of SQLAlchemy sessions.
- [ ] Preserve current penalties, group multipliers, beneficial bonuses, and returned field names.
- [ ] Run the Task 1 tests and confirm they pass.

### Task 3: Harden configuration, OCR, and DeepSeek clients

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/ocr.py`
- Modify: `backend/ai_analyze.py`
- Create: `backend/.env.example`
- Create: `backend/tests/test_providers.py`

**Interfaces:**
- Produces: `get_database_url() -> str | None`.
- Produces: `get_deepseek_client() -> OpenAI` with a clear configuration exception.
- Produces: `build_fallback_report(...) -> dict` for analysis degradation.

- [ ] Make database configuration optional and prefer `DATABASE_URL` when present.
- [ ] Validate Baidu credentials before requesting a token.
- [ ] Remove image Base64 and full OCR response logs.
- [ ] Add explicit token and OCR request timeouts and safe provider error mapping.
- [ ] Create the DeepSeek client lazily instead of at import time.
- [ ] Add deterministic fallback report generation for `/analyze`.
- [ ] Add tests for missing credentials, provider failures, and fallback report structure.
- [ ] Run `pytest backend/tests/test_providers.py -v` and confirm it passes.

### Task 4: Make Flask routes serverless-safe and database-optional

**Files:**
- Modify: `backend/app.py`
- Create: `backend/persistence.py`
- Create: `backend/tests/test_routes.py`

**Interfaces:**
- Produces: `save_scan(result, body) -> int | None`.
- Produces: `load_history(user_id, limit=20) -> list[dict]`.
- Produces: `load_daily(user_id) -> dict | None`.

- [ ] Configure CORS from `ALLOWED_ORIGINS`, allowing localhost during development.
- [ ] Add request-size and JSON validation for image endpoints.
- [ ] Make scan persistence best-effort and skip it when no database is configured.
- [ ] Return empty compatible history and daily payloads when persistence is unavailable.
- [ ] Make wiki cache reads/writes optional and use DeepSeek directly when no database exists.
- [ ] Use deterministic analysis output when DeepSeek fails inside `/analyze` or `/compare`.
- [ ] Add a global error handler that keeps the existing response envelope.
- [ ] Add route tests with mocked OCR and AI providers.
- [ ] Run `pytest backend/tests/test_routes.py -v` and confirm it passes.

### Task 5: Add the Vercel backend project entrypoint

**Files:**
- Create: `backend/api/index.py`
- Create: `backend/vercel.json`
- Modify: `backend/requirements.txt`
- Modify: `backend/.gitignore`
- Modify: `backend/README.md`

**Interfaces:**
- Produces: a Vercel Python function exporting `app`.
- Consumes: environment variables documented in `.env.example`.

- [ ] Export the Flask application from `api/index.py` with the backend root on `sys.path`.
- [ ] Route all incoming paths to the Flask function and include `data/csv/**` and the classifier model in the function bundle.
- [ ] Configure a 60-second maximum duration for OCR and AI requests.
- [ ] Pin production dependency version ranges and add pytest only to `requirements-dev.txt`.
- [ ] Document Vercel Root Directory, environment variables, and local commands.
- [ ] Run `python -c "from api.index import app; print(app.url_map)"` from `backend/` and confirm all routes import without secrets or a database.

### Task 6: Verify and deploy a backend preview

**Files:**
- Modify only if verification finds defects in the files above.

**Interfaces:**
- Produces: a Vercel Preview URL for the backend.

- [ ] Create an isolated virtual environment or use the configured workspace Python runtime.
- [ ] Install `backend/requirements.txt` and `backend/requirements-dev.txt`.
- [ ] Run `pytest -v` from `backend/`.
- [ ] Run the Flask import smoke test.
- [ ] Deploy `backend/` as a Vercel preview without production promotion.
- [ ] Do not configure or transmit real secrets through shell command arguments; give the user the exact Vercel dashboard variable names instead.

### Task 7: Connect the frontend after backend credentials are configured

**Files:**
- No repository changes unless the final backend route contract differs unexpectedly.

**Interfaces:**
- Consumes: the final backend HTTPS URL.

- [ ] In the frontend Vercel project, set `VITE_API_BASE_URL` to the backend deployment URL.
- [ ] Redeploy the frontend preview.
- [ ] Verify health, OCR analysis, AI comparison, AI chat, and wiki AI lookup after the user adds rotated provider credentials in Vercel.

