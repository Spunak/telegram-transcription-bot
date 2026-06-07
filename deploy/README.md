# Deployment Notes

This folder contains optional deployment templates. The main setup guides live in `docs/`.

## Systemd Template

`deploy/systemd/telegram-transcription-bot.service` is a template for Linux servers. Review and adjust:

- `User`
- `Group`
- `WorkingDirectory`
- `EnvironmentFile`
- `ExecStart`

Create `.env` from `.env.example` on the server and fill at least:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS`

If `ENABLE_SUMMARY=true`, also set:

- `OPENAI_API_KEY`
- `SUMMARY_MODEL`

## Docker

Use `docker-compose.yml` and the instructions in `docs/DOCKER.md`.

## Portainer

Use `docs/PORTAINER.md`. Set secrets in Portainer Environment Variables, not in repository files.
