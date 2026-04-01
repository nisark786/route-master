# Route Management Production Runbook

This runbook is the fastest safe path to launch production on Kubernetes.

For a free public launch without buying a domain, use the `nip.io` workflow in section 2B.

## 1. Prerequisites

- AWS account + IAM permissions for EKS/ECR/RDS/Route53/ACM.
- `kubectl` and `helm` installed locally.
- EKS context configured (`kubectl config current-context` points to prod cluster).
- Production TLS certificate already provisioned in ACM and wired to ingress controller.

## 2. Prepare private values

1. Copy:
   - `infra/k8s/values/production.private.example.yaml`
2. Save as:
   - `infra/k8s/values/production.private.yaml`
3. Fill all placeholders (`__REQUIRED__`, ECR repos/tags, real secrets).
4. Keep this file out of git.

## 2B. Free Public Host (`nip.io`) setup

If you do not have a paid domain yet:

```powershell
powershell -File infra/k8s/scripts/setup-public-beta-nipio.ps1 `
  -PrivateValues infra/k8s/values/production.private.yaml
```

What this script does:
- installs/updates `ingress-nginx` (LoadBalancer),
- installs/updates `cert-manager`,
- applies `letsencrypt-prod` ClusterIssuer,
- detects public LB address and builds `*.nip.io` host,
- generates `infra/k8s/values/public-beta.generated.yaml`,
- validates rendered manifests.

If your cluster cannot auto-detect LB address, pass host manually:

```powershell
powershell -File infra/k8s/scripts/setup-public-beta-nipio.ps1 `
  -SkipInfraInstall `
  -NipHost "<your-public-ip>.nip.io" `
  -PrivateValues infra/k8s/values/production.private.yaml
```

## 3. Validate production manifest

```powershell
powershell -File infra/k8s/scripts/prod-readiness-check.ps1 `
  -ReleaseName route-management `
  -PrivateValues infra/k8s/values/production.private.yaml
```

The check fails if it sees:
- example domains,
- localhost/local config,
- default/test/dev secrets,
- unresolved placeholders.

## 4. Deploy

```powershell
powershell -File infra/k8s/scripts/deploy-production.ps1 `
  -ReleaseName route-management `
  -Namespace route-prod `
  -PrivateValues infra/k8s/values/production.private.yaml
```

For free `nip.io` launch:

```powershell
powershell -File infra/k8s/scripts/deploy-production.ps1 `
  -ReleaseName route-management `
  -Namespace route-prod `
  -Environment public-beta.generated `
  -PrivateValues infra/k8s/values/production.private.yaml `
  -AllowTestPaymentKeys
```

What this does:
- runs readiness check,
- `helm upgrade --install --wait`,
- runs smoke checks against gateway/core/ai/root.

## 5. Post-deploy verification

- `kubectl get pods -n route-prod`
- `kubectl get ingress -n route-prod`
- `kubectl get svc -n route-prod`
- validate UI login, product CRUD, route assignment, chat, AI assistant.

## 6. Rollback

```powershell
helm history route-management -n route-prod
helm rollback route-management <REVISION> -n route-prod --wait
```

## 7. Immediate hardening after go-live

1. Rotate all sensitive keys.
2. Move runtime secrets to AWS Secrets Manager + External Secrets.
3. Enable CloudWatch alarms and billing alerts.
4. Schedule DB backup/restore drill.
