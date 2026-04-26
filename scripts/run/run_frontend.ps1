$ErrorActionPreference = 'Stop'

Write-Output "Starting frontend at http://127.0.0.1:5500"
Set-Location giao-dien/public
$pythonExe = "../../.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
	throw "Python virtual environment not found at $pythonExe"
}

& $pythonExe -m http.server 5500
