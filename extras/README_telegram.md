# Optional: Telegram front-end

This lets you send a PPD/EST/PIF file to a Telegram bot and get a draft estimate + notes
back in chat, using the same backend as the web app - nothing is duplicated.

## Setup

1. Make sure the main app works first: `python run.py` from the project root, with
   `ANTHROPIC_API_KEY` set in `.env` (required for the AI extraction step).
2. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram, get its token.
3. Install the extra dependency:
   ```bash
   pip install python-telegram-bot==21.*
   ```
4. Add to your `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your-bot-token-here
   BACKEND_URL=http://127.0.0.1:8000
   ```
5. In one terminal: `python run.py` (the web backend)
   In another terminal: `python extras/telegram_bot.py`

Send a PIF/PPD/EST file to your bot in Telegram (as a Document, not compressed photo, for
best quality on PDFs) and it will reply with draft parameters, an estimate, and notes -
always labelled DRAFT, for your engineer to review before any real use.

To make this reachable from anywhere (not just your own machine), you'd deploy the
backend (`run.py`) on a server you control and point `BACKEND_URL` at it - the bot script
itself doesn't change.
