$ErrorActionPreference = 'Stop'

$composeFile = "infra/docker/docker-compose.yml"

if (-not (Test-Path $composeFile)) {
    throw "Compose file not found: $composeFile"
}

Write-Output "Starting web service stack (db, api, streamlit)..."
cmd /c "docker compose -f $composeFile up -d --build"

if ($LASTEXITCODE -ne 0) {
    throw "Failed to start web service stack. Ensure Docker Desktop is running."
}

Write-Output "Web service stack started successfully."
Write-Output "Streamlit URL: http://127.0.0.1:8501"
Write-Output "API URL:      http://127.0.0.1:8000"
Write-Output "API Health:   http://127.0.0.1:8000/health"
