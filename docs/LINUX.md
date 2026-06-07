# Linux

## Setup

```bash
cp .env.example .env
nano .env
chmod +x scripts/setup-linux.sh scripts/run-linux.sh
./scripts/setup-linux.sh
```

Install `ffmpeg` with your package manager if it is not already available.

## Run

```bash
./scripts/run-linux.sh
```

## Manual Run

```bash
. .venv/bin/activate
python -m src.main
```
