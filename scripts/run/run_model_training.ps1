$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Write-Output "Training conversion model and generating experiment metrics..."
& $pythonExe etl/transformation/train_conversion_model.py

if ($LASTEXITCODE -ne 0) {
    throw "Model training failed with exit code $LASTEXITCODE"
}

Write-Output "Done. Artifacts in data/curated/model_eval and data/curated/models"
