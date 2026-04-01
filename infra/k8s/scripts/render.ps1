param(
  [string]$Environment = "staging",
  [string]$ReleaseName = "route-management"
)

$valuesFile = Join-Path $PSScriptRoot "..\values\$Environment.yaml"
$chartPath = Join-Path $PSScriptRoot "..\helm\route-management"

if (-not (Test-Path $valuesFile)) {
  Write-Error "Values file not found: $valuesFile"
  exit 1
}

helm template $ReleaseName $chartPath -f $valuesFile
