"""
Run this ONCE locally to generate your TELEGRAM_SESSION_STR.
Copy the output string into your .env / GitHub Secrets.

Usage:
    pip install telethon
    python gen_session.py
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID   = input("Enter your API_ID: ").strip()
API_HASH = input("Enter your API_HASH: ").strip()

async def main():
    async with TelegramClient(StringSession(), int(API_ID), API_HASH) as client:
        session_str = client.session.save()
        print("\n" + "=" * 60)
        print("✅ Your TELEGRAM_SESSION_STR (save this in .env / Secrets):")
        print("=" * 60)
        print(session_str)
        print("=" * 60 + "\n")

asyncio.run(main())
