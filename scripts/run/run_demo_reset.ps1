$ErrorActionPreference = 'Stop'

$root = Resolve-Path "e:/DoAnTotNghiep"
Set-Location $root

$sourceData = Join-Path $root "data/data_extended.csv"
$baselineData = Join-Path $root "data/raw/demo_baseline_data_extended.csv"

if (-not (Test-Path $sourceData)) {
    throw "Missing source dataset: $sourceData"
}

if (-not (Test-Path $baselineData)) {
    Write-Output "Baseline dataset not found. Creating baseline snapshot from current data_extended.csv"
    New-Item -ItemType Directory -Force -Path (Split-Path $baselineData -Parent) | Out-Null
    Copy-Item $sourceData $baselineData -Force
}

Write-Output "Restoring deterministic demo dataset..."
Copy-Item $baselineData $sourceData -Force

Write-Output "Rebuilding Spark quality output..."
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run/run_spark_quality.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "run_spark_quality.ps1 failed with exit code $LASTEXITCODE"
}

Write-Output "Rebuilding Spark recommendation output..."
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run/run_spark_recommendation.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "run_spark_recommendation.ps1 failed with exit code $LASTEXITCODE"
}

Write-Output "Rebuilding model artifacts..."
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run/run_model_training.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "run_model_training.ps1 failed with exit code $LASTEXITCODE"
}

Write-Output "Running full quality gate..."
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run/run_full_quality_gate.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "run_full_quality_gate.ps1 failed with exit code $LASTEXITCODE"
}

Write-Output "Demo reset completed successfully."
Write-Output "You can now start API and frontend for a deterministic defense demo."
