$ErrorActionPreference = 'Stop'

$pythonPath = (Get-Command python).Source
if ($pythonPath -like "*WindowsApps*") {
    $pythonPath = "C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe"
}

$env:PYSPARK_PYTHON = $pythonPath
$env:PYSPARK_DRIVER_PYTHON = $pythonPath

Write-Output "Running Spark budget recommendation job..."
cmd /c "spark-submit spark/jobs/budget_recommendation_job.py"

if ($LASTEXITCODE -ne 0) {
    throw "Spark recommendation job failed with exit code $LASTEXITCODE"
}

Write-Output "Done. Output saved to data/curated/budget_recommendations"
