Title: Unify backend configuration via .env (WEB_HOST/WEB_PORT) and share with frontend

Date: 2025-10-19
Author: Droid (Factory AI)

Summary
- Introduce `.env`-driven backend configuration for host/port so both backend and frontend stay aligned without manual edits.

Scope
- Backend (FastAPI/Uvicorn): read `WEB_HOST`/`WEB_PORT` from the root `.env` (overridden by CLI args).
- Frontend (Electron + Vite): load root `.env` and expose them as `VITE_WEB_HOST`/`VITE_WEB_PORT`; default axios baseURL uses these values.

Implementation
- Backend: `opencontext/cli.py` now respects `WEB_HOST`/`WEB_PORT` if provided (priority: CLI args > ENV > config defaults).
- Frontend build config: set `envDir: '..'` and `define` Vite vars to map from `process.env.WEB_HOST/WEB_PORT`.
- Frontend axios: default baseURL built from `VITE_WEB_HOST`/`VITE_WEB_PORT`, still supports runtime override via IPC `backend:get-port`.
- Docs: Updated `.env.example` and `docs/ENV_CONFIGURATION.md` to include `WEB_HOST`/`WEB_PORT`.

How to Use
1) Copy example and edit:
   cp .env.example .env
2) Set values:
   WEB_HOST=127.0.0.1
   WEB_PORT=8000
3) Start dev:
   ./start-dev.sh

Notes
- In packaged app the backend may choose an available port at runtime; the renderer still updates via IPC, so the defaults only affect initial baseURL in dev.
- This change does not alter security posture; the existing `.env` load applies.

PR: <to be added>
