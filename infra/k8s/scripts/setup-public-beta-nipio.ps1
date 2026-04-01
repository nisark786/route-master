param(
  [string]$Namespace = "ingress-nginx",
  [string]$ReleaseName = "route-management",
  [string]$AppNamespace = "route-prod",
  [string]$PrivateValues = "infra/k8s/values/production.private.yaml",
  [string]$Email = "support.routemaster@gmail.com",
  [string]$NipHost = "",
  [switch]$SkipInfraInstall
)

$ErrorActionPreference = "Stop"

function Get-IngressAddress {
  param([string]$SvcNamespace)
  $svcJson = kubectl get svc ingress-nginx-controller -n $SvcNamespace -o json | ConvertFrom-Json
  $lb = $svcJson.status.loadBalancer.ingress
  if ($null -eq $lb -or $lb.Count -eq 0) {
    return $null
  }
  if ($lb[0].ip) {
    return $lb[0].ip
  }
  if ($lb[0].hostname) {
    return $lb[0].hostname
  }
  return $null
}

if (-not $SkipInfraInstall) {
  Write-Host "Ensuring helm repos..."
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx | Out-Null
  helm repo add jetstack https://charts.jetstack.io | Out-Null
  helm repo update | Out-Null

  Write-Host "Installing/upgrading ingress-nginx..."
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx `
    -n $Namespace --create-namespace `
    --set controller.service.type=LoadBalancer `
    --wait --timeout 15m

  Write-Host "Installing/upgrading cert-manager..."
  helm upgrade --install cert-manager jetstack/cert-manager `
    -n cert-manager --create-namespace `
    --set crds.enabled=true `
    --wait --timeout 15m

  $issuerPath = Join-Path $PSScriptRoot "..\manifests\cert-manager-clusterissuer-letsencrypt-prod.yaml"
  $issuerContent = Get-Content $issuerPath -Raw
  $issuerContent = $issuerContent -replace "support\.routemaster@gmail\.com", $Email
  $tmpIssuer = Join-Path $env:TEMP "route-issuer.yaml"
  Set-Content -Path $tmpIssuer -Value $issuerContent -Encoding UTF8
  kubectl apply -f $tmpIssuer | Out-Null
}

if ([string]::IsNullOrWhiteSpace($NipHost)) {
  Write-Host "Waiting for LoadBalancer address..."
  $address = $null
  for ($i = 0; $i -lt 40; $i++) {
    $address = Get-IngressAddress -SvcNamespace $Namespace
    if ($address) { break }
    Start-Sleep -Seconds 15
  }
  if (-not $address) {
    throw "Could not get ingress-nginx LoadBalancer address. Pass -NipHost manually or check kubectl get svc -n $Namespace"
  }

  $nipHost = if ($address -match "^\d+\.\d+\.\d+\.\d+$") {
    "$address.nip.io"
  } else {
    $address
  }
} else {
  $nipHost = $NipHost
}

Write-Host "Detected public host: $nipHost"

$baseValuesPath = Join-Path $PSScriptRoot "..\values\public-beta.nipio.yaml"
$generatedValuesPath = Join-Path $PSScriptRoot "..\values\public-beta.generated.yaml"
$content = Get-Content $baseValuesPath -Raw
$content = $content.Replace("__NIP_IO_HOST__", $nipHost)
Set-Content -Path $generatedValuesPath -Value $content -Encoding UTF8

Write-Host "Running dry readiness check..."
powershell -File (Join-Path $PSScriptRoot "prod-readiness-check.ps1") `
  -ReleaseName $ReleaseName `
  -ProdValues $generatedValuesPath `
  -PrivateValues $PrivateValues `
  -AllowTestPaymentKeys
if ($LASTEXITCODE -ne 0) {
  throw "Readiness check failed for generated values."
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Generated values: $generatedValuesPath"
Write-Host "Public URL host: $nipHost"
Write-Host ""
Write-Host "Next deploy command:"
Write-Host "powershell -File infra/k8s/scripts/deploy-production.ps1 -ReleaseName $ReleaseName -Namespace $AppNamespace -Environment public-beta.generated -PrivateValues $PrivateValues -AllowTestPaymentKeys"
