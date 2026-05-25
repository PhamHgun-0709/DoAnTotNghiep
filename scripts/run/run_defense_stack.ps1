param(
    [switch]$WithStreamlit
)

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "e:/DoAnTotNghiep"

Write-Output "Starting defense stack from $root"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", "Set-Location '$root'; ./scripts/run/run_api.ps1"
)

if ($WithStreamlit) {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", "Set-Location '$root'; ./scripts/run/run_streamlit.ps1"
    )
}

Write-Output "Defense stack launched in separate terminals."
Write-Output "API: http://127.0.0.1:8000"
if ($WithStreamlit) {
    Write-Output "Streamlit: http://127.0.0.1:8501"
}
