$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Write-Output "Running API smoke test..."
& $pythonExe tests/api_smoke_test.py

if ($LASTEXITCODE -ne 0) {
    throw "API smoke test failed with exit code $LASTEXITCODE"
}

Write-Output "API smoke test finished successfully."
