$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot "scripts/run/run_webservice_stack.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Cannot find script: $scriptPath"
}

powershell -ExecutionPolicy Bypass -File $scriptPath
