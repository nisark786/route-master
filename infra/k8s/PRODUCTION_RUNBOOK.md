# Route Management Production Runbook (Hybrid AWS)

This runbook launches production with EKS for compute and managed AWS services for stateful data.

Target architecture:
- EKS: backend, ai-service, gateway, frontend, celery workers/beat.
- AWS managed data: RDS PostgreSQL, DocumentDB, Amazon MQ RabbitMQ.
- EKS in this phase: Redis + Qdrant.

## 1. Prerequisites

- AWS IAM permissions for EKS/ECR/RDS/DocumentDB/AmazonMQ/SecretsManager.
- `aws`, `kubectl`, `helm`, `terraform` installed.
- EKS context configured to `route-master-prod`.
- `infra/k8s/values/production.private.yaml` prepared from example.

## 2. Provision managed data layer (Terraform)

1. Edit `infra/aws/terraform/terraform.tfvars` and set:
   - `enable_managed_data_layer = true`
   - `eks_cluster_name = "route-master-prod"`
2. Apply:

```powershell
cd infra/aws/terraform
terraform init
terraform plan
terraform apply
```

3. Capture outputs:
   - `rds_endpoint`, `rds_port`, `rds_core_db_name`, `rds_ai_db_name`
   - `documentdb_endpoint`, `documentdb_port`
   - `amazon_mq_endpoint`
   - `managed_data_secret_arn`

## 3. Prepare private values for external services

Update `infra/k8s/values/production.private.yaml`:
- Set `externalServices.postgresCore.enabled = true` and host/port from RDS output.
- Set `externalServices.postgresAi.enabled = true` and host/port from RDS output.
- Set `externalServices.rabbitmq.enabled = true` and `brokerUrl` from Amazon MQ endpoint/credentials.
- Set `externalServices.mongo.enabled = true` and `uri` from DocumentDB endpoint/credentials.
- Disable in-cluster StatefulSets:
  - `postgresCore.enabled = false`
  - `postgresAi.enabled = false`
  - `rabbitmq.enabled = false`
  - `mongo.enabled = false`

Keep Redis and Qdrant enabled in this phase.

## 4. Planned downtime cutover (data migration)

1. Freeze writes:
   - put UI/API in maintenance mode OR scale write paths/workers down temporarily.
2. Export in-cluster Postgres and import to RDS.
3. Create AI database in RDS (`rds_ai_db_name`) if not already present.
4. Migrate Mongo datasets to DocumentDB (if Mongo-backed features are active).
5. Deploy with external service values (section 5).
6. Run migrations and smoke tests.
7. Resume writes/workers.

## 5. Deploy production (temporary ELB URL)

Readiness:

```powershell
powershell -File infra/k8s/scripts/prod-readiness-check.ps1 `
  -ReleaseName route-management `
  -PrivateValues infra/k8s/values/production.private.yaml `
  -AllowTestPaymentKeys
```

Deploy:

```powershell
powershell -File infra/k8s/scripts/deploy-production.ps1 `
  -ReleaseName route-management `
  -Namespace route-prod `
  -Environment public-beta.generated `
  -PrivateValues infra/k8s/values/production.private.yaml `
  -AllowTestPaymentKeys
```

## 6. Verify

- `kubectl get pods -n route-prod`
- `kubectl get pvc -n route-prod` (no pending PVC for disabled services)
- `kubectl get ingress -n route-prod`
- Health checks:
  - `/healthz`
  - `/api/core/health/`
  - `/api/ai/health`
- Functional checks:
  - login, product CRUD, route/assignment flow, driver sync, chat, AI assistant.

## 7. Rollback

1. Rollback Helm release:

```powershell
helm history route-management -n route-prod
helm rollback route-management <REVISION> -n route-prod --wait
```

2. Restore previous in-cluster DB stack only if required and re-point values to prior endpoints.

## 8. Post go-live hardening

1. Rotate all credentials used during migration.
2. Shift app runtime secrets to Secrets Manager + External Secrets Operator.
3. Add CloudWatch alarms (RDS CPU/storage/connections, MQ health, EKS pod restarts).
4. Run backup/restore drill for RDS and DocumentDB.
