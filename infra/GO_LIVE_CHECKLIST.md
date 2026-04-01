# RouteMaster Go-Live Checklist (Dev -> Staging -> Production)

This checklist is tailored for the current repository structure:
- `core_services` (Django + Celery + Channels)
- `ai_service` (FastAPI + Qdrant + Celery)
- `frontend/route_management` (React web admin)
- `mobile apk/route_management_app` (Flutter app)
- `infra` (Nginx, k8s, AWS utilities)

---

## 1) Feature Freeze Gate (Dev Complete)

- Freeze v1 scope and stop adding new features.
- Confirm critical flows work end-to-end:
  - Auth: login, refresh, `me`, role/permission checks.
  - Billing: registration, renewal create-order, renewal complete.
  - Operations: route create/edit, assignment lifecycle, execution updates.
  - Chat: text + voice, delivery/seen, push notification.
  - AI: sync knowledge, assistant chat, copilot generation.
- Resolve all P0 and P1 bugs.
- Remove dead code and stale configs discovered during debugging.

Exit criteria:
- No known crash-level issue in dev.
- All core user journeys manually validated.

---

## 2) Code Quality Gate

- Backend:
  - `python manage.py check` passes in `core_services`.
  - Migrations are clean and reversible.
  - Critical DB indexes exist for slow endpoints.
- AI service:
  - Provider config tested (`huggingface` and/or `groq`).
  - RAG request logs include stage timings (`search_ms`, `llm_ms`, `total_ms`).
- Frontend/mobile:
  - No blocking console/runtime errors on key pages.
  - Auth/session expiration handling verified.

Exit criteria:
- No startup/runtime import errors.
- No blocking lint/type/runtime errors in release paths.

---

## 3) Security & Config Gate

- Split secrets/config by environment (`dev`, `staging`, `prod`):
  - DB creds, JWT secrets, payment keys, AI keys, Firebase keys.
- Confirm security settings:
  - Strict `ALLOWED_HOSTS`, CORS origin allowlist.
  - Cookie flags (`HttpOnly`, `Secure`, `SameSite`) per env.
  - Rate limiting for auth, billing, and chat message APIs.
- Rotate any leaked/test keys before production.

Exit criteria:
- No production secrets in repo.
- All sensitive settings sourced from env/secrets manager.

---

## 4) Staging Deployment Gate (Kubernetes)

- Build and push immutable images for:
  - `core_services`, `celery_worker`, `celery_beat`
  - `ai_service`, `ai_celery_worker`
  - `frontend` (if not hosted externally)
- Deploy infra dependencies in staging:
  - Postgres, Redis, RabbitMQ, Mongo, Qdrant.
- Apply staging k8s manifests/helm values.
- Run DB migrations once after deploy.
- Run smoke tests:
  - `/api/auth/me`
  - `/api/company/profile`
  - `/api/company-admin/dashboard/overview`
  - `/api/ai/chat`
  - websocket chat connect path

Exit criteria:
- All services healthy.
- Smoke tests pass.

---

## 5) Performance & Reliability Gate

- Define baseline SLO targets (example):
  - Login p95 < 800ms
  - Dashboard API p95 < 500ms
  - AI assistant p95 < 4s
- Load test critical APIs and websocket concurrency.
- Confirm retries/timeouts:
  - Payment APIs
  - AI provider calls
  - internal service calls
- Validate graceful fallback behavior:
  - AI model unavailable -> no 500 crash
  - payment create-order failure -> safe user error

Exit criteria:
- p95 and error rate within agreed thresholds.

---

## 6) Observability Gate

- Metrics:
  - Prometheus targets up for backend, AI, DB, broker, cache.
- Dashboards:
  - Grafana panels for auth, billing, ops, chat, AI timings.
- Alerts:
  - 5xx surge, high latency, queue backlog, DB connectivity, pod restarts.
- Logs:
  - Correlation IDs or request identifiers across gateway/core/ai paths.

Exit criteria:
- Team can detect and diagnose incidents quickly.

---

## 7) Production Readiness Gate

- Backup and recovery tested:
  - Postgres backup + restore drill.
  - Recovery runbook documented.
- Rollback strategy validated:
  - previous image rollback tested in staging.
- Billing and limits:
  - budget alarms configured in AWS.
  - non-critical resources have cost controls.
- Incident readiness:
  - on-call owner and escalation contacts set.

Exit criteria:
- Rollback, restore, and alerting are proven.

---

## 8) Production Release Process

1. Tag release (`vX.Y.Z`).
2. Build and push images with immutable tags.
3. Deploy to production (rolling/canary).
4. Run post-deploy smoke tests.
5. Monitor dashboards for 30-60 min.
6. If regression appears, rollback immediately.

---

## 9) Post-Go-Live (First 2 Weeks)

- Daily review:
  - latency, 5xx, queue lag, failed payments, AI fallback frequency.
- Capture top user pain points and patch quickly.
- Add tests for every production incident root cause.
- Plan v1.1 hardening sprint before adding major new features.

---

## 10) Project-Specific Priority Order (Recommended)

1. Stabilize billing and subscription lifecycle.
2. Stabilize operations lifecycle state transitions.
3. Stabilize chat reliability (message + push + reconnect).
4. Stabilize AI latency and fallback quality.
5. Polish UI/UX and non-critical enhancements.
