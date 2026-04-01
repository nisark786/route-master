param(
  [string]$ReleaseName = "route-management",
  [string]$ChartPath = "",
  [string]$BaseValues = "",
  [string]$ProdValues = "",
  [string]$PrivateValues = "",
  [switch]$AllowTestPaymentKeys
)

if ([string]::IsNullOrWhiteSpace($ChartPath)) {
  $ChartPath = Join-Path $PSScriptRoot "..\helm\route-management"
}
if ([string]::IsNullOrWhiteSpace($BaseValues)) {
  $BaseValues = Join-Path $PSScriptRoot "..\helm\route-management\values.yaml"
}
if ([string]::IsNullOrWhiteSpace($ProdValues)) {
  $ProdValues = Join-Path $PSScriptRoot "..\values\production.yaml"
}

foreach ($path in @($ChartPath, $BaseValues, $ProdValues)) {
  if (-not (Test-Path $path)) {
    Write-Error "Missing required path: $path"
    exit 1
  }
}

$helmCmd = @("helm", "template", $ReleaseName, $ChartPath, "-f", $BaseValues, "-f", $ProdValues)
if (-not [string]::IsNullOrWhiteSpace($PrivateValues)) {
  if (-not (Test-Path $PrivateValues)) {
    Write-Error "Private values file not found: $PrivateValues"
    exit 1
  }
  $helmCmd += @("-f", $PrivateValues)
}

$rendered = & $helmCmd[0] $helmCmd[1..($helmCmd.Length - 1)] 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host $rendered
  Write-Error "helm template failed."
  exit 1
}

$manifest = $rendered -join "`n"

$blockedPatterns = @(
  @{ Pattern = "__REQUIRED__"; Message = "Required placeholder values still present." },
  @{ Pattern = "__NIP_IO_HOST__"; Message = "NIP host placeholder is still present." },
  @{ Pattern = "change-me-"; Message = "Default insecure secrets still present." },
  @{ Pattern = "route\.example\.com"; Message = "Example domain is still configured." },
  @{ Pattern = "route\.local"; Message = "Local domain still present in production manifest." },
  @{ Pattern = "dev-secret"; Message = "Development secret detected in production manifest." }
)

if (-not $AllowTestPaymentKeys) {
  $blockedPatterns += @{ Pattern = "rzp_test_"; Message = "Razorpay test key detected in production manifest." }
}

$hasBlockers = $false
foreach ($entry in $blockedPatterns) {
  if ($manifest -match $entry.Pattern) {
    Write-Host ("[BLOCKER] " + $entry.Message) -ForegroundColor Red
    $hasBlockers = $true
  }
}

if ($hasBlockers) {
  Write-Host ""
  Write-Host "Production readiness check failed. Fix blockers, then re-run." -ForegroundColor Yellow
  exit 1
}

Write-Host "Production readiness check passed." -ForegroundColor Green
