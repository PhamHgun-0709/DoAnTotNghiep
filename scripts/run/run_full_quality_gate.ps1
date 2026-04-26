$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

$tests = @(
    @{ Name = "Spark output smoke test"; Script = "tests/spark_output_smoke_test.py" },
    @{ Name = "Model artifact test"; Script = "tests/model_artifacts_test.py" },
    @{ Name = "API smoke test"; Script = "tests/api_smoke_test.py" }
)

$startTime = Get-Date
Write-Output "=== Full Quality Gate Started: $($startTime.ToString('yyyy-MM-dd HH:mm:ss')) ==="

foreach ($test in $tests) {
    Write-Output ""
    Write-Output ">>> Running $($test.Name)..."
    & $pythonExe $test.Script
    if ($LASTEXITCODE -ne 0) {
        throw "$($test.Name) failed with exit code $LASTEXITCODE"
    }
    Write-Output "<<< $($test.Name) PASSED"
}

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Output ""
Write-Output "=== Full Quality Gate PASSED in $([math]::Round($duration.TotalSeconds, 1))s ==="