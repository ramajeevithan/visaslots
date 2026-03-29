# 🛂 H1B Visa OFC Slot Monitor

Monitors multiple free sources for H1B OFC appointment slot availability in India
and sends instant Telegram alerts when slots are mentioned. Runs free via GitHub Actions
every 20 minutes — zero cost, zero maintenance.

---

## 📡 Sources Monitored

| Source | What it watches | Method |
|---|---|---|
| **redbus2us.com** | Comments & articles about H1B slot openings | HTML scraping |
| **visaslots.info** | Slot availability table for India consulates | HTML scraping |
| **@AllIndiaWorkVisaAutoSlotNotifier** | Telegram bot posting H1B + H4 slot alerts | Telethon API |
| **@All_INDIA_H1B_VisaDiscussion** | Telegram H1B community discussion | Telethon API |

---

## ⚙️ Setup (one-time, ~20 minutes)

### Step 1 — Create a Telegram Bot (to receive alerts)

1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** → this is your `TELEGRAM_BOT_TOKEN`
4. Open Telegram → search **@userinfobot** → it replies with your chat ID
5. Copy your **chat ID** → this is your `TELEGRAM_CHAT_ID`
6. Start a chat with your new bot (send it any message so it can message you back)

### Step 2 — Get Telegram API credentials (to read public channels)

1. Go to **https://my.telegram.org** and log in with your phone number
2. Click **"API development tools"**
3. Fill in the form (app name: anything, platform: Desktop)
4. Copy **App api_id** → `TELEGRAM_API_ID`
5. Copy **App api_hash** → `TELEGRAM_API_HASH`

### Step 3 — Generate a session string (one-time, run locally)

```bash
pip install telethon
python gen_session.py
```

- Enter your API ID and API Hash when prompted
- Telegram will send a code to your phone — enter it
- The script prints your **session string** → copy it → `TELEGRAM_SESSION_STR`

### Step 4 — Set up GitHub Actions (free hosting)

1. Create a **new private GitHub repo** (keep it private — your session string is sensitive)
2. Push all these files to the repo:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/visa-slot-monitor.git
   git push -u origin main
   ```
3. Go to your repo → **Settings → Secrets and variables → Actions**
4. Add each of these as a **Repository Secret**:

   | Secret name | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
   | `TELEGRAM_CHAT_ID` | Your personal chat ID |
   | `TELEGRAM_API_ID` | From my.telegram.org |
   | `TELEGRAM_API_HASH` | From my.telegram.org |
   | `TELEGRAM_SESSION_STR` | From gen_session.py output |

5. Go to **Actions tab** → enable workflows if prompted
6. Click **"H1B Visa Slot Monitor"** → **"Run workflow"** to test it manually first

---

## 🧪 Running Locally (for testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in your credentials
cp .env.example .env
# Edit .env with your values

# Run once
python monitor.py
```

---

## 🎛️ Customization

### Filter by specific consulate
In `monitor.py`, edit the `CONSULATE_FILTER` list:
```python
CONSULATE_FILTER = ["mumbai"]        # Only Mumbai alerts
CONSULATE_FILTER = ["delhi", "hyderabad"]  # Multiple cities
CONSULATE_FILTER = []                # All consulates (default)
```

### Change check frequency
In `.github/workflows/monitor.yml`, edit the cron schedule:
```yaml
- cron: "*/20 * * * *"   # Every 20 minutes (default)
- cron: "*/10 * * * *"   # Every 10 minutes (more aggressive)
- cron: "0 * * * *"      # Every hour (conservative)
```
> ⚠️ Don't go below 10 minutes — some sites may rate-limit you.

### Add H4 visa monitoring
Add to `VISA_KEYWORDS` in `monitor.py`:
```python
"h4", "h-4", "dependent"
```

---

## 📁 File Structure

```
visa-slot-monitor/
├── monitor.py              # Main monitor script
├── gen_session.py          # One-time session string generator
├── requirements.txt        # Python dependencies
├── .env.example            # Template for your credentials
├── .gitignore              # Keeps .env and session files out of git
└── .github/
    └── workflows/
        └── monitor.yml     # GitHub Actions schedule
```

---

## 🔔 What an Alert Looks Like

```
📣 H1B Slot Alert — Telegram
🕐 2025-08-15 14:32 UTC

📢 @AllIndiaWorkVisaAutoSlotNotifier:

H1B OFC appointment slots available in Mumbai for September!
Book immediately.

🔗 View source
⚡ Book now: usvisascheduling.com
```

---

## ⚠️ Disclaimer

This tool is for **personal notification use only**. It does not auto-book appointments.
Always review and manually complete your booking on the official portal.
Use responsibly and in accordance with the terms of service of each monitored site.
