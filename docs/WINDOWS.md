# Windows

## Setup

1. Install Python 3.12 or newer.
2. Install `ffmpeg` and make sure it is available on `PATH`.
3. Double-click `configure-windows.bat`.
4. Fill `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS`.

The setup script creates `.venv`, installs `requirements.txt`, and creates `.env` if it does not exist.

## Run

Double-click `run-windows.bat`.

The terminal window stays open after errors so you can read the logs.

## Manual Run

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.main
```
