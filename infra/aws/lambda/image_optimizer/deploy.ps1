$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..\..\..")
$envFile = Join-Path $repoRoot ".env"
$zipPath = Join-Path $scriptRoot "build\image-optimizer.zip"

if (-not (Test-Path $zipPath)) {
    throw "Package not found at $zipPath. Run .\package.ps1 first."
}

if (-not (Test-Path $envFile)) {
    throw "Env file not found at $envFile."
}

$containerCommand = @"
pip install --no-cache-dir boto3 >/tmp/pip-boto3.log &&
python /workspace/infra/aws/lambda/image_optimizer/deploy.py
"@

docker run --rm `
    --env-file "$envFile" `
    -e "LAMBDA_PACKAGE_PATH=/workspace/infra/aws/lambda/image_optimizer/build/image-optimizer.zip" `
    -v "${repoRoot}:/workspace" `
    python:3.12-slim `
    /bin/sh -lc $containerCommand
