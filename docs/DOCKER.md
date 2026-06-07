# Docker

## Local Docker Compose

Create and edit `.env`:

```bash
cp .env.example .env
nano .env
```

Start the bot:

```bash
docker compose up -d --build
docker compose logs -f bot
```

Stop the bot:

```bash
docker compose down
```

## Required Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS`

## Optional Summary Variables

- `ENABLE_SUMMARY=true`
- `OPENAI_API_KEY`
- `SUMMARY_MODEL`

`docker-compose.yml` does not contain real secrets. Values come from your local `.env` or the environment where Compose runs.
