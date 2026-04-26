$ErrorActionPreference = 'Stop'

$pythonExe = "e:/DoAnTotNghiep/.venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Write-Output "Starting Streamlit app at http://127.0.0.1:8501"
& $pythonExe -m streamlit run giao-dien/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
