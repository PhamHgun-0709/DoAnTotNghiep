$ErrorActionPreference = 'Stop'

$pythonPath = (Get-Command python).Source
if ($pythonPath -like "*WindowsApps*") {
    $pythonPath = "C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe"
}

$env:PYSPARK_PYTHON = $pythonPath
$env:PYSPARK_DRIVER_PYTHON = $pythonPath

Write-Output "Running Spark ad quality job..."
cmd /c "spark-submit spark/jobs/ad_quality_job.py"

if ($LASTEXITCODE -ne 0) {
    throw "Spark job failed with exit code $LASTEXITCODE"
}

Write-Output "Done. Output saved to data/processed/ad_quality"
