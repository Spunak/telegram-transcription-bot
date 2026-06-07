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
