# Windows

## Setup

1. Install Python 3.12 or newer.
2. Double-click `configure-windows.bat`.
3. Fill `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS`.

The setup script creates `.venv`, installs `requirements.txt`, creates `.env` if it does not exist, and checks whether FFmpeg is available.

## FFmpeg

FFmpeg is required for converting Telegram voice/audio/video files before transcription.

Recommended install command:

```powershell
winget install Gyan.FFmpeg
```

Then close and reopen the terminal and verify:

```powershell
ffmpeg -version
```

`configure-windows.bat` checks for FFmpeg and can optionally try to install it with winget. If FFmpeg is still missing, the setup completes with a warning so you can install it manually.

## Windows Unknown Publisher Warning

Windows may show an "Unknown publisher" warning when double-clicking `.bat` files downloaded from GitHub. This is expected for unsigned batch files. Only run scripts after reviewing and trusting the source. If you trust this repository, you can click Run.

You can also unblock the startup files:

```powershell
Unblock-File .\configure-windows.bat
Unblock-File .\run-windows.bat
Unblock-File .\scripts\setup-windows.ps1
Unblock-File .\scripts\run-windows.ps1
```

Or unblock the repository folder recursively:

```powershell
Get-ChildItem -Recurse | Unblock-File
```

Using `git clone` may avoid some download-zone warnings compared with downloading and extracting a ZIP file.

## Run

Double-click `run-windows.bat`.

If FFmpeg is missing, `run-windows.bat` warns before starting and asks whether to continue. The terminal window stays open after errors so you can read the logs.

## Manual Run

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.main
```
