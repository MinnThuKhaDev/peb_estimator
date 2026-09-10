"""
Optional Telegram front-end for the PEB Estimate Assistant.

Send a PIF/PPD/EST file (xlsx, pdf, or image) to your bot in Telegram; it drafts building
parameters + a weight estimate breakdown + short engineering notes, and replies in chat.
Every reply is explicitly labelled DRAFT - for your engineer to review and approve.

This talks directly to your already-running local backend (python run.py in the project
root), so the estimator/database logic is never duplicated - only requires:

    pip install python-telegram-bot==21.* requests python-dotenv

Environment variables (put in a .env next to this file, or export them):
    TELEGRAM_BOT_TOKEN     from @BotFather
    BACKEND_URL            your deployed backend URL, e.g. https://your-app.onrender.com
    BOT_SERVICE_USERNAME   a dedicated (non-admin) account created via the admin panel
                            for this bot to log in as — don't reuse the admin account
    BOT_SERVICE_PASSWORD   that account's password

The backend now requires login on every endpoint, so create a plain (non-admin) user
just for the bot from the app's admin panel first, e.g. username "telegram-bot".

Run this as its own always-on process (a small free worker on Render, or any machine
with internet), separate from the web backend:
    python extras/telegram_bot.py
"""
import io
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
SERVICE_USERNAME = os.getenv("BOT_SERVICE_USERNAME")
SERVICE_PASSWORD = os.getenv("BOT_SERVICE_PASSWORD")

_token_cache = {"token": None, "expires": 0}


def get_auth_headers() -> dict:
    """Logs in once and caches the JWT for ~7 hours (server tokens last 8h by default)."""
    if _token_cache["token"] and time.time() < _token_cache["expires"]:
        return {"Authorization": f"Bearer {_token_cache['token']}"}
    if not SERVICE_USERNAME or not SERVICE_PASSWORD:
        raise RuntimeError(
            "Set BOT_SERVICE_USERNAME and BOT_SERVICE_PASSWORD (create that user in the "
            "admin panel first) so the bot can log in to the backend."
        )
    resp = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": SERVICE_USERNAME, "password": SERVICE_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("requires_2fa"):
        raise RuntimeError(
            "The bot's service account has 2FA enabled — disable 2FA on that account, "
            "since the bot can't complete an interactive 2FA prompt."
        )
    _token_cache["token"] = data["token"]
    _token_cache["expires"] = time.time() + 7 * 3600
    return {"Authorization": f"Bearer {_token_cache['token']}"}

DRAFT_HEADER = (
    "\u26a0\ufe0f DRAFT OUTPUT \u2014 for your engineer's review and approval only.\n"
    "Not for construction. No wind/seismic analysis or member design was performed.\n\n"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a PIF / PPD / EST file (xlsx, pdf, or image) and I'll draft building "
        "parameters, a weight estimate breakdown, and short engineering notes.\n\n"
        "Everything I send back is a DRAFT only - your engineer must review and approve "
        "it before any real use. I never produce certified or stamped drawings."
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    tg_file = None
    filename = "upload.bin"

    if msg.document:
        tg_file = await msg.document.get_file()
        filename = msg.document.file_name or filename
    elif msg.photo:
        tg_file = await msg.photo[-1].get_file()
        filename = "photo.jpg"
    else:
        await msg.reply_text("Please send this as a file/document (or photo), not plain text.")
        return

    await msg.reply_text("Reading file and asking the AI to draft parameters...")

    buf = io.BytesIO()
    await tg_file.download_to_memory(out=buf)
    buf.seek(0)

    note = msg.caption or None

    try:
        headers = get_auth_headers()
        resp = requests.post(
            f"{BACKEND_URL}/api/ai-extract",
            files={"file": (filename, buf, "application/octet-stream")},
            data={"note": note} if note else {},
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        await msg.reply_text(
            f"Could not reach the AI extraction endpoint: {e}\n\n"
            f"Make sure the backend is deployed/running and GEMINI_API_KEY is set in "
            f"its environment, and that BOT_SERVICE_USERNAME/PASSWORD are correct."
        )
        return

    fields, notes = data.get("fields"), data.get("notes", "")

    reply = DRAFT_HEADER + "EXTRACTED PARAMETERS:\n"
    if fields:
        for k, v in fields.items():
            if v is not None:
                reply += f"  - {k}: {v}\n"
    else:
        reply += "  (could not confidently extract structured values - see notes below)\n"

    if fields and fields.get("width") and fields.get("length"):
        try:
            est_payload = {
                "name": filename, "width": float(fields["width"]), "length": float(fields["length"]),
                "eave_height": float(fields.get("eave_height") or 9),
                "wind_speed": float(fields.get("wind_speed") or 130),
                "live_load": float(fields.get("live_load") or 0.57),
                "enclosure": fields.get("enclosure") or "Enclosed",
                "frame_type": fields.get("frame_type") or "CS",
                "has_mezz": bool(fields.get("has_mezz")), "mezz_area": float(fields.get("mezz_area") or 0),
                "has_crane": bool(fields.get("has_crane")), "crane_cap": float(fields.get("crane_cap") or 0),
                "crane_len": float(fields.get("crane_len") or 0),
                "has_canopy": bool(fields.get("has_canopy")), "canopy_area": float(fields.get("canopy_area") or 0),
            }
            est_resp = requests.post(
                f"{BACKEND_URL}/api/estimate", json=est_payload,
                headers=get_auth_headers(), timeout=30,
            )
            est_resp.raise_for_status()
            est = est_resp.json()
            reply += (
                f"\nDRAFT ESTIMATE:\n"
                f"  Area: {est['area']:.1f} m^2\n"
                f"  Predicted rate: {est['kgm2']:.2f} kg/m^2\n"
                f"  Estimated total weight: {round(est['grand_total']):,} kg\n"
                f"  Overall: {est['overall_kgm2']:.2f} kg/m^2\n"
                f"  (based on {est['historical_count']} historical project(s) in the local database)\n"
            )
        except Exception as e:
            reply += f"\n(Could not compute a weight estimate automatically: {e})\n"

    reply += f"\nDRAFT ENGINEERING NOTES:\n{notes}"

    for i in range(0, len(reply), 3800):
        await msg.reply_text(reply[i:i + 3800])


def main():
    if not BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your environment or .env file first.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    print("Telegram bot running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
