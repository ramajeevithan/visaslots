"""
US H1B Visa OFC Slot Monitor
Monitors redbus2us.com, visaslots.info, and Telegram public channels
Sends alerts to your personal Telegram bot when H1B OFC slots are found
"""

import os
import re
import json
import hashlib
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────
# CONFIGURATION (set in .env or GitHub Secrets)
# ─────────────────────────────────────────
# Bot account (for sending alerts)
TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")    # From @BotFather
TELEGRAM_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID")      # Your personal chat ID

# User account (for scraping Telegram channels)
TELEGRAM_API_ID      = os.getenv("TELEGRAM_API_ID")       # From my.telegram.org
TELEGRAM_API_HASH    = os.getenv("TELEGRAM_API_HASH")     # From my.telegram.org
TELEGRAM_USER_SESSION_STR = os.getenv("TELEGRAM_USER_SESSION_STR")  # Generated via gen_session.py with personal account

# H1B-specific keywords — any match triggers alert
VISA_KEYWORDS = [
    "h1b", "h-1b", "h1", "h 1b",
    "employer", "work visa", "employment visa",
    "h4", "h-4",           # often posted alongside H1B
    "ofc", "fingerprint",  # OFC appointment terms
    "i-129", "i129",       # H1B petition form
]

# Indian consulates — leave empty [] to monitor ALL
# e.g. ["mumbai", "delhi", "hyderabad", "chennai", "kolkata"]
CONSULATE_FILTER = []

# Telegram public channels to monitor (H1B specific — free, no subscription)
TELEGRAM_CHANNELS = [
    "AllIndiaWorkVisaAutoSlotNotifier",  # H1B + H4 bot slot alerts
    "All_INDIA_H1B_VisaDiscussion",     # H1B community discussion
]

STATE_FILE = "seen_items.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# STATE MANAGEMENT (deduplication)
# ─────────────────────────────────────────

def load_seen() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def make_hash(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


# ─────────────────────────────────────────
# KEYWORD MATCHING
# ─────────────────────────────────────────

def is_relevant(text: str) -> bool:
    """Returns True if the text is H1B-related and mentions slot availability."""
    t = text.lower()
    slot_words = ["slot", "available", "availability", "appointment",
                  "opening", "opened", "open", "book", "schedule"]
    has_slot     = any(w in t for w in slot_words)
    has_visa     = any(v in t for v in VISA_KEYWORDS)
    has_consulate = not CONSULATE_FILTER or any(c in t for c in CONSULATE_FILTER)
    return has_slot and has_visa and has_consulate


# ─────────────────────────────────────────
# ALERT SENDER
# ─────────────────────────────────────────

def send_alert(source: str, text: str, url: str = ""):
    """Send a formatted Telegram alert to yourself."""
    emoji_map = {
        "RedBus2US": "📰",
        "VisaSlots": "📊",
        "Telegram":  "📣",
    }
    emoji = emoji_map.get(source, "🔔")
    now   = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    msg = (
        f"{emoji} <b>H1B Slot Alert — {source}</b>\n"
        f"🕐 {now}\n\n"
        f"{text[:600]}"
    )
    if url:
        msg += f"\n\n🔗 <a href='{url}'>View source</a>"
    msg += (
        "\n\n⚡ <b>Book now:</b> "
        "<a href='https://www.usvisascheduling.com/en-US/ofc-schedule/'>"
        "usvisascheduling.com</a>"
    )

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(api_url, json={
            "chat_id":                  TELEGRAM_CHAT_ID,
            "text":                     msg,
            "parse_mode":               "HTML",
            "disable_web_page_preview": False,
        }, timeout=10)
        r.raise_for_status()
        log.info(f"  ✅ Alert sent [{source}]")
    except requests.exceptions.HTTPError as e:
        log.error(f"  ❌ Alert failed [{source}]: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        log.error(f"  ❌ Alert failed [{source}]: {e}")


# ─────────────────────────────────────────
# SOURCE 1: redbus2us.com
# ─────────────────────────────────────────

REDBUS_URLS = [
    "https://redbus2us.com/h1b-visa-slot-news/",
    "https://redbus2us.com/category/h1b-visa-news/",
    "https://redbus2us.com/us-visa-appointment-india/",
]

def scrape_redbus(seen: set) -> int:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SlotMonitor/1.0)"}
    total_alerts = 0

    for url in REDBUS_URLS:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Comments first, then article paragraphs as fallback
            items = soup.select(".comment-body p, .comment-content p, article p")
            if not items:
                items = soup.select("p")

            new_count = 0
            for el in items:
                text = el.get_text(strip=True)
                if len(text) < 30:
                    continue
                h = make_hash(text)
                if h in seen:
                    continue
                seen.add(h)
                new_count += 1
                if is_relevant(text):
                    send_alert("RedBus2US", text, url)
                    total_alerts += 1

            log.info(f"  [RedBus2US] {url.split('/')[-2]}: {new_count} new items")

        except Exception as e:
            log.error(f"  [RedBus2US] Error — {url}: {e}")

    return total_alerts


# ─────────────────────────────────────────
# SOURCE 2: visaslots.info
# ─────────────────────────────────────────

VISASLOTS_URLS = [
    "https://visaslots.info/",
    "https://visaslots.info/h1b",
    "https://visaslots.info/india",
]

INDIA_TERMS = ["india", "mumbai", "delhi", "chennai", "hyderabad", "kolkata", "new delhi"]

def scrape_visaslots(seen: set) -> int:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SlotMonitor/1.0)"}
    total_alerts = 0

    for url in VISASLOTS_URLS:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Prefer structured rows; fall back to generic blocks
            candidates = soup.select(
                "table tr, .slot-row, [class*='slot'], [class*='avail'], [class*='visa']"
            )
            if not candidates:
                candidates = soup.select("div, p, li")

            new_count = 0
            for el in candidates:
                text = el.get_text(separator=" ", strip=True)
                if len(text) < 15 or len(text) > 1000:
                    continue
                h = make_hash(text)
                if h in seen:
                    continue
                seen.add(h)
                new_count += 1

                is_india = any(t in text.lower() for t in INDIA_TERMS)
                if is_india and is_relevant(text):
                    send_alert("VisaSlots", text, url)
                    total_alerts += 1

            log.info(f"  [VisaSlots] {url}: {new_count} new items")

        except Exception as e:
            log.error(f"  [VisaSlots] Error — {url}: {e}")

    return total_alerts


# ─────────────────────────────────────────
# SOURCE 3: Telegram public channels
# ─────────────────────────────────────────

async def scrape_telegram_channels(seen: set) -> int:
    """Read the last 20 messages from each free H1B Telegram channel.
    
    Requires a USER account session (not a bot account).
    To generate: Run gen_session.py with your personal Telegram account.
    """
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_USER_SESSION_STR]):
        log.warning("  [Telegram] Skipping — user session not set. Run gen_session.py with personal account.")
        return 0

    total_alerts = 0
    try:
        client = TelegramClient(
            StringSession(TELEGRAM_USER_SESSION_STR),
            int(TELEGRAM_API_ID),
            TELEGRAM_API_HASH,
        )
        await client.start()

        for channel in TELEGRAM_CHANNELS:
            try:
                entity   = await client.get_entity(channel)
                messages = await client.get_messages(entity, limit=20)

                new_count = 0
                for msg in messages:
                    if not msg.text:
                        continue
                    h = make_hash(msg.text)
                    if h in seen:
                        continue
                    seen.add(h)
                    new_count += 1
                    if is_relevant(msg.text):
                        send_alert(
                            "Telegram",
                            f"📢 @{channel}:\n\n{msg.text}",
                            f"https://t.me/{channel}",
                        )
                        total_alerts += 1

                log.info(f"  [Telegram] @{channel}: {new_count} new messages")

            except Exception as e:
                log.error(f"  [Telegram] Error reading @{channel}: {e}")

        await client.disconnect()

    except Exception as e:
        log.error(f"  [Telegram] Client error: {e}")

    return total_alerts


# ─────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────

async def run():
    log.info("=" * 55)
    log.info("🔍  H1B Visa OFC Slot Monitor — Starting check")
    log.info("=" * 55)

    seen  = load_seen()
    total = 0

    log.info("📰 Checking RedBus2US...")
    total += scrape_redbus(seen)

    log.info("📊 Checking VisaSlots.info...")
    total += scrape_visaslots(seen)

    log.info("📣 Checking Telegram channels...")
    total += await scrape_telegram_channels(seen)

    save_seen(seen)

    if total == 0:
        log.info("😴 No new H1B slot mentions found this run.")
    else:
        log.info(f"🎯 {total} new H1B slot alert(s) sent to Telegram!")

    log.info("✅ Check complete.\n")

if __name__ == "__main__":
    asyncio.run(run())
