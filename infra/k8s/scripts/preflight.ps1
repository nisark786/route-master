Write-Host "Route Management Kubernetes preflight"

$checks = @(
  @{ Name = "helm"; Command = "helm version --short" },
  @{ Name = "kubectl"; Command = "kubectl version --client" },
  @{ Name = "docker"; Command = "docker --version" }
)

$failed = $false

foreach ($check in $checks) {
  Write-Host ""
  Write-Host "Checking $($check.Name)..."
  try {
    Invoke-Expression $check.Command | Write-Host
  }
  catch {
    Write-Host "$($check.Name) is not available." -ForegroundColor Yellow
    $failed = $true
  }
}

Write-Host ""
if ($failed) {
  Write-Host "One or more required tools are missing." -ForegroundColor Yellow
  exit 1
}

Write-Host "All required tools are available." -ForegroundColor Green
