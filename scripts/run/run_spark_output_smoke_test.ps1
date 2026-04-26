$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Write-Output "Running Spark output smoke test..."
& $pythonExe tests/spark_output_smoke_test.py

if ($LASTEXITCODE -ne 0) {
    throw "Spark output smoke test failed with exit code $LASTEXITCODE"
}

Write-Output "Spark output smoke test finished successfully."
