import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) if os.getenv("ADMIN_ID", "0").isdigit() else 0
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://stale-bears-sneeze.loca.lt").strip()

# Twilio Voice Calling sozlamalari
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "").strip()

DB_PATH = BASE_DIR / "database" / "bot.db"
VOICE_TEMP_DIR = BASE_DIR / "temp_audio"
VOICE_TEMP_DIR.mkdir(exist_ok=True)
