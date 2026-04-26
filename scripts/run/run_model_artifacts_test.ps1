$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Write-Output "Running model artifact test..."
& $pythonExe tests/model_artifacts_test.py

if ($LASTEXITCODE -ne 0) {
    throw "Model artifact test failed with exit code $LASTEXITCODE"
}

Write-Output "Model artifact test finished successfully."
