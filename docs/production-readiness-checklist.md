# Production Readiness Checklist

## 1. Environment and Access
- Create production namespace and context.
- Confirm production kubeconfig works from deploy runner.
- Restrict production access to minimum required users.
- Enable GitHub Environment protection for `production` (manual approval).

## 2. Secrets and Config
- Prepare `production.private.yaml` with real values.
- Verify payment keys, email SMTP, JWT secrets, and internal auth secrets.
- Verify S3 and CloudFront values for media uploads.
- Ensure no placeholder values like `__REQUIRED__` remain.

## 3. Data and Persistence
- Confirm PVC sizes for Postgres, Mongo, Qdrant, Redis, RabbitMQ.
- Enable automated backups for Postgres and Mongo.
- Test backup restore on a non-production namespace.

## 4. Networking and Security
- Configure production host/domain and TLS certificate.
- Validate ingress routes (`/`, `/api`, `/ws`).
- Confirm network policies allow required app/data traffic only.
- Enforce HTTPS and secure cookie/session settings.

## 5. Deployment and Rollback
- Run `Deploy Production` with manual approval.
- Confirm all pods are `Ready` and smoke checks return `200`.
- Record release revision after successful deploy.
- Test rollback command once:
  - `helm rollback route-management <REVISION> -n route-prod --wait --timeout 15m`

## 6. Observability and Operations
- Confirm metrics scraping works (backend, gateway, AI).
- Configure Grafana dashboards and alert rules.
- Configure alert channels (email/Slack/Telegram).
- Define on-call ownership and incident response flow.

## 7. Business Flow Validation
- Company registration and login.
- Subscription lifecycle and renewal.
- Route creation, assignment, driver execution, completion.
- Chat, audio, and notifications flow.
- AI assistant and copilot basic scenario checks.

## 8. Go-Live
- Freeze staging baseline.
- Announce deployment window.
- Deploy production.
- Run post-launch smoke tests.
- Monitor errors/alerts for first 24 hours.
