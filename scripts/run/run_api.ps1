$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Write-Output "Starting API at http://127.0.0.1:8000"
if (-not $env:DATABASE_URL) {
    $dbPassword = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "<set-a-password>" }
    $env:DATABASE_URL = "postgresql+psycopg://postgres:$dbPassword@localhost:5432/ad_analytics"
    Write-Output "DATABASE_URL not set. Using default: $env:DATABASE_URL"
}
& $pythonExe -m uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 8000 --reload
