$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment not found. Run configure-windows.bat first."
}

if (-not (Test-Path -LiteralPath ".env")) {
    throw ".env not found. Run configure-windows.bat first."
}

Write-Host "Starting Telegram Transcription Bot..."
& $venvPython -m src.main
exit $LASTEXITCODE
