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

function Test-FFmpegAvailable {
    return [bool](Get-Command ffmpeg -ErrorAction SilentlyContinue)
}

function Confirm-Yes {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Answer
    )

    return $Answer.Trim().ToLowerInvariant() -in @("y", "yes")
}

if (-not (Test-FFmpegAvailable)) {
    Write-Host ""
    Write-Warning "FFmpeg is not available. The bot may start, but media conversion will fail."
    Write-Host "Install with: winget install Gyan.FFmpeg"
    Write-Host "Then reopen the terminal and run: ffmpeg -version"
    Write-Host ""

    $answer = Read-Host "Start anyway? [y/N]"
    if (-not (Confirm-Yes -Answer $answer)) {
        Write-Host "Startup cancelled."
        exit 0
    }
}

Write-Host "Starting Telegram Transcription Bot..."
& $venvPython -m src.main
exit $LASTEXITCODE
