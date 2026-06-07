$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Get-PythonCommand {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @("py", "-3")
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @("python")
    }

    throw "Python was not found. Install Python 3.12 or newer and enable 'Add python.exe to PATH'."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    $pythonCommand = Get-PythonCommand
    $pythonExecutable = $pythonCommand[0]
    $pythonPrefixArgs = @()
    if ($pythonCommand.Length -gt 1) {
        $pythonPrefixArgs = $pythonCommand[1..($pythonCommand.Length - 1)]
    }

    & $pythonExecutable @pythonPrefixArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

function ConvertFrom-SecureStringPlainText {
    param(
        [Parameter(Mandatory = $true)]
        [System.Security.SecureString] $Value
    )

    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Set-EnvFileValue {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [string] $Value
    )

    $lines = Get-Content -LiteralPath $Path
    $updated = $false
    $newLines = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Name))=") {
            "$Name=$Value"
            $updated = $true
        }
        else {
            $line
        }
    }

    if (-not $updated) {
        $newLines += "$Name=$Value"
    }

    Set-Content -LiteralPath $Path -Value $newLines -Encoding UTF8
}

function Test-FFmpegAvailable {
    return [bool](Get-Command ffmpeg -ErrorAction SilentlyContinue)
}

function Write-FFmpegInstallInstructions {
    Write-Host ""
    Write-Warning "FFmpeg is required for audio/video conversion."
    Write-Host "The bot can start without it, but transcription of Telegram media will fail."
    Write-Host ""
    Write-Host "Recommended install command:"
    Write-Host "  winget install Gyan.FFmpeg"
    Write-Host ""
    Write-Host "After installing FFmpeg, close and reopen the terminal, then run:"
    Write-Host "  ffmpeg -version"
    Write-Host "  run-windows.bat"
}

function Confirm-Yes {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Answer
    )

    return $Answer.Trim().ToLowerInvariant() -in @("y", "yes")
}

function Invoke-FFmpegSetupCheck {
    if (Test-FFmpegAvailable) {
        Write-Host "FFmpeg found."
        return
    }

    Write-FFmpegInstallInstructions

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host ""
        Write-Host "winget was not found. Install FFmpeg manually, then reopen the terminal."
        return
    }

    $answer = Read-Host "Install FFmpeg with winget now? [y/N]"
    if (Confirm-Yes -Answer $answer) {
        & winget install Gyan.FFmpeg
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "winget did not complete successfully. Install FFmpeg manually if needed."
        }
        Write-Host ""
        Write-Host "Close and reopen this terminal before starting the bot, then verify with ``ffmpeg -version``."
        return
    }

    Write-Host ""
    Write-Host "Skipping FFmpeg installation. Install it later with:"
    Write-Host "  winget install Gyan.FFmpeg"
    Write-Host "Then close and reopen the terminal and run:"
    Write-Host "  ffmpeg -version"
}

Write-Host "Setting up Telegram Transcription Bot..."

Invoke-Python -Arguments @("--version")

if (-not (Test-Path -LiteralPath ".venv")) {
    Invoke-Python -Arguments @("-m", "venv", ".venv")
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment Python was not found at $venvPython"
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

Invoke-FFmpegSetupCheck

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example."
}

$token = Read-Host "Telegram bot token (leave empty to edit .env manually)" -AsSecureString
$tokenPlain = ConvertFrom-SecureStringPlainText -Value $token
if ($tokenPlain) {
    Set-EnvFileValue -Path ".env" -Name "TELEGRAM_BOT_TOKEN" -Value $tokenPlain
}

$allowedUserIds = Read-Host "Telegram allowed user IDs, comma-separated (required)"
if ($allowedUserIds) {
    Set-EnvFileValue -Path ".env" -Name "TELEGRAM_ALLOWED_USER_IDS" -Value $allowedUserIds
}

if (-not $tokenPlain -or -not $allowedUserIds) {
    Write-Host "Opening .env so you can fill the required values."
    Start-Process notepad.exe -ArgumentList (Join-Path $ProjectRoot ".env") -Wait
}

Write-Host "Setup complete. Use run-windows.bat to start the bot."
Write-Host "If Windows shows an unknown publisher warning for the batch files, see docs/WINDOWS.md."
