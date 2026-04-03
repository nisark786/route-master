param(
  [string]$ReleaseName = "route-management",
  [string]$Namespace = "route-prod",
  [string]$Environment = "production",
  [string]$PrivateValues = "",
  [switch]$AllowTestPaymentKeys,
  [switch]$SkipReadinessCheck,
  [switch]$DryRun
)

$chartPath = Join-Path $PSScriptRoot "..\helm\route-management"
$baseValues = Join-Path $chartPath "values.yaml"
$envValues = Join-Path $PSScriptRoot "..\values\$Environment.yaml"

if (-not (Test-Path $chartPath)) { Write-Error "Chart not found: $chartPath"; exit 1 }
if (-not (Test-Path $baseValues)) { Write-Error "Base values not found: $baseValues"; exit 1 }
if (-not (Test-Path $envValues)) { Write-Error "Environment values not found: $envValues"; exit 1 }
if (-not [string]::IsNullOrWhiteSpace($PrivateValues) -and -not (Test-Path $PrivateValues)) {
  Write-Error "Private values file not found: $PrivateValues"
  exit 1
}

Write-Host "Checking required tools..."
try {
  helm version --short | Out-Null
} catch {
  Write-Error "helm is not available in PATH."
  exit 1
}
try {
  kubectl version --client=true | Out-Null
} catch {
  Write-Error "kubectl is not available in PATH."
  exit 1
}

if (-not $SkipReadinessCheck) {
  Write-Host "Running production readiness validation..."
  $checkScript = Join-Path $PSScriptRoot "prod-readiness-check.ps1"
  if ([string]::IsNullOrWhiteSpace($PrivateValues)) {
    & $checkScript -ReleaseName $ReleaseName -ChartPath $chartPath -BaseValues $baseValues -ProdValues $envValues -AllowTestPaymentKeys:$AllowTestPaymentKeys
  } else {
    & $checkScript -ReleaseName $ReleaseName -ChartPath $chartPath -BaseValues $baseValues -ProdValues $envValues -PrivateValues $PrivateValues -AllowTestPaymentKeys:$AllowTestPaymentKeys
  }
  if ($LASTEXITCODE -ne 0) {
    exit 1
  }
}

$helmArgs = @("upgrade", "--install", $ReleaseName, $chartPath, "-n", $Namespace, "--create-namespace", "-f", $baseValues, "-f", $envValues)
if (-not [string]::IsNullOrWhiteSpace($PrivateValues)) {
  $helmArgs += @("-f", $PrivateValues)
}

if ($DryRun) {
  Write-Host "Running Helm dry run..."
  & helm @helmArgs "--dry-run"
  exit $LASTEXITCODE
}

Write-Host "Deploying release to namespace '$Namespace'..."
& helm @helmArgs "--wait" "--timeout" "15m"
if ($LASTEXITCODE -ne 0) {
  Write-Error "Helm deploy failed."
  exit 1
}

Write-Host "Running post-deploy smoke checks..."
kubectl run smoke-prod-check -n $Namespace --rm -i --restart=Never --image=curlimages/curl --command -- sh -lc "set -e; echo gateway_healthz; curl -sS -o /dev/null -w '%{http_code}\n' http://$ReleaseName-gateway/healthz; echo core_health; curl -sS -o /dev/null -w '%{http_code}\n' http://$ReleaseName-gateway/api/core/health/; echo ai_auth_guard; curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{}' http://$ReleaseName-gateway/api/ai/chat; echo root; curl -sS -o /dev/null -w '%{http_code}\n' http://$ReleaseName-gateway/;"

Write-Host "Deployment completed." -ForegroundColor Green
