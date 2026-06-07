# Portainer

## Create Stack

1. Open Portainer.
2. Go to Stacks.
3. Choose Add stack.
4. Paste the contents of `docker-compose.yml`.

## Set Environment Variables

In the stack Environment Variables section, set:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS`

Optional summary settings:

- `ENABLE_SUMMARY=true`
- `OPENAI_API_KEY`
- `SUMMARY_MODEL`

Optional runtime settings:

- `TRANSCRIPTION_MODEL`
- `MAX_FILE_SIZE_MB`
- `MAX_MEDIA_MINUTES`
- `LOG_LEVEL`

## Deploy

1. Click Deploy the stack.
2. Open the stack logs.
3. Confirm the bot starts with long polling.

If the bot exits with missing required variables, edit the stack environment values and deploy again.
