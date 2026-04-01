$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $scriptRoot "build"
$packageRoot = Join-Path $buildRoot "package"
$zipPath = Join-Path $buildRoot "image-optimizer.zip"

if (Test-Path $buildRoot) {
    Remove-Item -Recurse -Force $buildRoot
}

New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null

$containerCommand = @"
pip install -r /var/task/requirements.txt -t /var/task/build/package &&
cp /var/task/handler.py /var/task/build/package/handler.py
"@

docker run --rm `
    --entrypoint /bin/sh `
    -v "${scriptRoot}:/var/task" `
    public.ecr.aws/lambda/python:3.12 `
    -lc $containerCommand

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zipPath
Write-Host "Built package: $zipPath"
