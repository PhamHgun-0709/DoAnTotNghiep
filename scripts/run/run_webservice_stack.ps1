$ErrorActionPreference = 'Stop'

$composeFile = "infra/docker/docker-compose.webservice.yml"

if (-not (Test-Path $composeFile)) {
    throw "Compose file not found: $composeFile"
}

Write-Output "Starting web service stack (db, api, web)..."
cmd /c "docker compose -f $composeFile up -d --build"

if ($LASTEXITCODE -ne 0) {
    throw "Failed to start web service stack. Ensure Docker Desktop is running."
}

Write-Output "Web service stack started successfully."
Write-Output "Web URL: http://127.0.0.1:8080"
Write-Output "API URL: http://127.0.0.1:8000"
Write-Output "Health:  http://127.0.0.1:8080/health"
