# Going live — free hosting, free database, in order

Do these in order. Everything here is free-tier. Total time: ~30–45 minutes.

## 0. First — rotate the leaked key
Your original upload had a real Anthropic API key sitting in a plain `.env` file.
Go to https://console.anthropic.com/ and revoke/regenerate it before doing anything
else. It's been removed from this package.

## 1. Put the code on GitHub (free)
1. Create a free account at github.com if you don't have one.
2. Create a new **private** repository, e.g. `peb-estimator`.
3. Upload this whole `peb_estimator` folder to it (drag-and-drop on github.com works,
   or `git init && git add . && git commit -m "init" && git push`).
   The `.gitignore` already excludes `.env` and the database file, so secrets won't
   be committed as long as you don't paste them into any file that isn't `.env`.

## 2. Free Postgres database
Pick one (both are genuinely free, no credit card required for the free tier):

- **Neon** (neon.tech) — sign up, "New Project", copy the connection string it
  gives you (starts with `postgresql://...`).
- **Supabase** (supabase.com) — sign up, "New Project", go to
  Project Settings → Database → Connection string ("URI" tab, use the "pooler"
  one for serverless hosts like Render).

Keep this connection string — you'll paste it into `DATABASE_URL` in step 4.

## 3. Free Gemini API key (for the AI Assistant tab)
Go to https://aistudio.google.com/app/apikey, sign in with a Google account,
click "Create API key". Copy it — you'll paste it into `GEMINI_API_KEY`.

## 4. Deploy the backend — Render.com (free web service)
1. Sign up at render.com (free, no card required for the free web service tier).
2. New → Web Service → connect your GitHub repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment**, add these variables:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Postgres string from step 2 |
   | `JWT_SECRET` | run `python -c "import os;print(os.urandom(32).hex())"` locally and paste the result |
   | `ENCRYPTION_KEY` | run `python -c "from app.crypto_fields import generate_key;print(generate_key())"` and paste the result |
   | `ADMIN_INITIAL_PASSWORD` | `PEB77777@mmvm` (or change it — only used the very first time the database is created) |
   | `AI_PROVIDER` | `gemini` |
   | `GEMINI_API_KEY` | the key from step 3 |
   | `ALLOWED_ORIGINS` | your Render URL once you know it, e.g. `https://peb-estimator.onrender.com` |
5. Click **Create Web Service**. Render builds and deploys it — you'll get a public
   URL like `https://peb-estimator.onrender.com`, reachable from any device with
   internet, anywhere.
6. **Free-tier note:** Render's free web services sleep after 15 minutes of no
   traffic and take ~30-60 seconds to wake up on the next request. That's normal on
   the free tier — upgrading to a paid instance ($7/mo) removes the sleep, if that
   ever matters to you.

## 5. First login
Open your Render URL. Log in with:
- Username: `admin`
- Password: whatever you set as `ADMIN_INITIAL_PASSWORD` (default `PEB77777@mmvm`)

From **Account & 2FA**, set up two-factor authentication on the admin account right
away — scan the QR code with Google Authenticator/Authy and confirm the 6-digit code.
From **Admin: Users**, create accounts for your team (each gets their own username
and password — never share the admin login).

## 6. Telegram bot (optional)
1. In Telegram, message **@BotFather** → `/newbot` → follow the prompts → copy the
   token it gives you.
2. In the app's Admin panel, create a plain (non-admin) account for the bot to use,
   e.g. username `telegram-bot`, and make sure 2FA is **off** for it.
3. Run `extras/telegram_bot.py` as its own always-on process — the easiest free
   option is another Render service (New → Background Worker, same repo):
   - **Build command:** `pip install -r requirements.txt python-telegram-bot`
   - **Start command:** `python extras/telegram_bot.py`
   - Environment variables: `TELEGRAM_BOT_TOKEN`, `BACKEND_URL` (your Render web
     service URL from step 4), `BOT_SERVICE_USERNAME`, `BOT_SERVICE_PASSWORD`.
4. Message your bot on Telegram — send it a file to test.

## 7. What's still manual / limitations to know about
- **DWG files** are accepted for upload and stored so you can download them again,
  but they can't be auto-read (DWG is Autodesk's closed binary format). For AI
  extraction or field auto-fill, export a PDF, image, or DXF instead.
- The free Postgres tiers (Neon/Supabase) and free Render web service both have
  storage/usage caps generous enough for this kind of tool, but check their current
  limits on their pricing pages if your usage grows a lot.
- This tool still only produces **draft, non-certified estimates** — that hasn't
  changed, and the app is upfront about it in its own banner and terms modal.
