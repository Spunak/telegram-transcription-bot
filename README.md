# Telegram Transcription Bot

Telegram Transcription Bot is a private Telegram bot for turning voice messages and media into searchable text. It transcribes Telegram voice, audio, video, and document media, supports selected media URLs, and uses local `faster-whisper` transcription instead of a transcription API.

Access is limited to configured Telegram User IDs. Optional AI summaries can be enabled separately with OpenAI settings.

## What it does

- Receives a Telegram voice message, audio file, video file, media document, or supported media URL
- Downloads or receives the media
- Converts it to a transcription-ready audio format with `ffmpeg`
- Transcribes it locally with `faster-whisper`
- Sends transcript text in Telegram and attaches the full transcript as a `.txt` file
- Optionally summarizes transcripts when `ENABLE_SUMMARY=true`

## Why this is useful

- Converts Telegram voice messages into searchable text
- Works locally without sending transcription audio to a transcription API
- Keeps access private with a Telegram User ID whitelist
- Handles voice, audio, video, document media, and supported URLs
- Can optionally summarize transcripts with OpenAI
- Works on Windows, Linux, Docker Compose, and Portainer

## Features

- Local faster-whisper transcription
- Telegram User ID whitelist
- Direct Telegram media support
- Selected URL media download through `yt-dlp`
- Optional Instagram cookie configuration
- Transcript chunking for Telegram message limits
- Full `.txt` transcript attachment
- Optional `/sum` and `/sumlang` summary flow
- Windows, Linux, Docker Compose, and Portainer setup docs

## Requirements

- Python 3.12 or newer
- `ffmpeg` installed and available on `PATH`
- Telegram bot token from BotFather
- Telegram User ID for each allowed user
- Optional: OpenAI API key and summary model when summaries are enabled

## Quick Start Windows

1. Double-click `configure-windows.bat`.
2. Enter `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS` when prompted.
3. Double-click `run-windows.bat`.

The setup script creates `.venv`, installs dependencies, and creates `.env` from `.env.example` if needed.

## Quick Start Linux

```bash
cp .env.example .env
nano .env
./scripts/setup-linux.sh
./scripts/run-linux.sh
```

If the shell scripts are not executable yet, run:

```bash
chmod +x scripts/setup-linux.sh scripts/run-linux.sh
```

## Docker Compose

```bash
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
```

Docker Compose reads variables from your local `.env`. Do not commit `.env`.

## Portainer

Use `docker-compose.yml` as a Portainer stack. Set required variables in the stack Environment Variables section:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS`

If summaries are enabled, also set:

- `ENABLE_SUMMARY=true`
- `OPENAI_API_KEY`
- `SUMMARY_MODEL`

See `docs/PORTAINER.md` for step-by-step instructions.

## Configuration

Required:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=
```

Optional:

```env
OPENAI_API_KEY=
ENABLE_SUMMARY=false
SUMMARY_MODEL=
TRANSCRIPTION_MODEL=turbo
WHISPER_LANGUAGE=auto
MAX_FILE_SIZE_MB=25
LOG_LEVEL=INFO
```

`OPENAI_API_KEY` is not required for transcription. It is only required when summaries are enabled.

`WHISPER_LANGUAGE=auto` enables automatic language detection. Set `WHISPER_LANGUAGE=de`, `WHISPER_LANGUAGE=en`, or another supported language code to force a specific transcription language.

## Transcription Models

`TRANSCRIPTION_MODEL` controls the local faster-whisper model used for transcription.

Recommended defaults:

- `TRANSCRIPTION_MODEL=turbo` for most users
- `TRANSCRIPTION_MODEL=large-v3` for maximum accuracy
- `TRANSCRIPTION_MODEL=small` for weaker machines

Common model choices:

| Model | Speed | Accuracy | Recommended use |
| --- | --- | --- | --- |
| `tiny` | Fastest | Lowest | Quick tests, very weak machines |
| `base` | Very fast | Basic | Short notes, simple audio, low-resource systems |
| `small` | Fast | Good | Weaker machines and everyday short clips |
| `medium` | Moderate | Better | Balanced accuracy when runtime is less critical |
| `large-v3` | Slow | Highest | Maximum accuracy and more difficult audio |
| `turbo` | Fast | High | Best default for most users |
| `distil-large-v3` | Fast | High | Good speed/accuracy balance on supported setups |

faster-whisper can also load supported Hugging Face or CTranslate2 model names and local model paths. Beginners should start with `turbo`, then switch to `small` for lower resource use or `large-v3` for maximum accuracy.

## Telegram User ID Whitelist

`TELEGRAM_ALLOWED_USER_IDS` is a comma-separated whitelist of numeric Telegram User IDs:

```env
TELEGRAM_ALLOWED_USER_IDS=your_telegram_user_id_here
```

The bot refuses to start safely when this value is missing or empty. Telegram bots normally do not receive user IP addresses, so access control uses Telegram User IDs, not IPs.

To find your Telegram User ID, message a trusted ID helper bot such as `@userinfobot`, or get the numeric ID from another trusted source before starting the bot.

## Optional Summary Feature

Summary is disabled by default:

```env
ENABLE_SUMMARY=false
```

To enable it:

```env
ENABLE_SUMMARY=true
OPENAI_API_KEY=your_openai_api_key_here
SUMMARY_MODEL=gpt-4o-mini
```

If summary is enabled without the required OpenAI settings, the bot exits with a clear startup error. Missing summary configuration does not affect normal transcription when `ENABLE_SUMMARY=false`.

## Security Notes

- Never commit `.env`, API keys, bot tokens, cookies, chat IDs, Telegram User IDs, or private logs.
- Keep `_private_local_archive_DO_NOT_COMMIT/` local only.
- `.dockerignore` keeps local secrets, private archives, caches, logs, and data files out of Docker build contexts.
- Review `git status --short` and `git diff` before publishing.
- Use Telegram User IDs for authorization, not IP addresses.
- Keep `LOG_LEVEL=INFO` for normal use.

## Troubleshooting

- `Missing required environment variables`: fill `.env`, especially `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS`.
- `Unauthorized.`: your Telegram User ID is not in the whitelist.
- `Server misconfigured: ffmpeg unavailable.`: install `ffmpeg` or set `FFMPEG_BIN`.
- Instagram link fails: configure `INSTAGRAM_COOKIE_FILE`, `INSTAGRAM_COOKIES_FROM_BROWSER`, or `INSTAGRAM_COOKIES_TXT`.
- Large media rejected: adjust `MAX_MEDIA_MINUTES` or `MAX_FILE_SIZE_MB`.
- Summary disabled: set `ENABLE_SUMMARY=true`, `OPENAI_API_KEY`, and `SUMMARY_MODEL`.

## License

MIT. See `LICENSE`.
