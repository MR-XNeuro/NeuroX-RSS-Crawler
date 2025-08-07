import os
from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
from bs4 import BeautifulSoup
import hashlib
import random
import redis
from redis.connection import SSLConnection
from datetime import datetime, timedelta, timezone

# === تنظیمات ===
BACKENDLESS_APP_ID = os.getenv("BACKENDLESS_APP_ID")
BACKENDLESS_API_KEY = os.getenv("BACKENDLESS_API_KEY")
BACKENDLESS_API_URL = os.getenv("BACKENDLESS_API_URL")
BACKENDLESS_TABLE = "Posts"
API_URL = f"{BACKENDLESS_API_URL}/{BACKENDLESS_APP_ID}/{BACKENDLESS_API_KEY}/data/{BACKENDLESS_TABLE}"

TARGET_SITES_FILE = "target_sites.txt"
PLATFORMS = ["WordPress", "Blogspot", "Tumblr", "X"]

# --- اتصال به Redis با استفاده از REDIS_URL از .env ---
REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.Redis.from_url(REDIS_URL, connection_class=SSLConnection)

# --- لود کردن لینک‌های هدف ---
def load_target_sites():
    try:
        with open(TARGET_SITES_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print("⚠️ Failed to load target sites:", e)
        return []

# --- استخراج متن از سایت ---
def extract_text_from_site(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 80)
        return text.strip()
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

# --- لود تبلیغات ---
def load_promos(file_path="promo_texts.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines
    except Exception as e:
        print("⚠️ Failed to load promos:", e)
        return []

PROMO_LINES = load_promos()

# --- تولید پست برای Backendless ---
def generate_post(text, source_url):
    promo = random.choice(PROMO_LINES) if PROMO_LINES else ""
    platform = random.choice(PLATFORMS)
    now = datetime.now(timezone.utc)
    return {
        "title": "Betting Risk Exposed",
        "description": text + "\n\n" + promo,
        "imageUrl": "",
        "sourceUrl": source_url,
        "targetPlatform": platform,
        "scheduledAt": (now + timedelta(minutes=random.randint(5, 60))).strftime("%Y-%m-%d %H:%M:%S"),
        "status": "scheduled",
        "createdAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "updatedAt": now.strftime("%Y-%m-%d %H:%M:%S")
    }

# --- ارسال پست ---
def post_to_backendless(data):
    try:
        r = requests.post(API_URL, json=data)
        r.raise_for_status()
        print("✅ Sent to Backendless:", data["title"], "→", data["targetPlatform"])
    except Exception as e:
        print("❌ Failed to send post:", e)

# --- اجرای اصلی ---
    TARGET_SITES = load_target_sites()
    for site in TARGET_SITES:
        print("🔍 Scraping:", site)
        text = extract_text_from_site(site)
        if not text:
            continue
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        if redis_client.sismember("seen_hashes", content_hash):
            print("⏭️ Duplicate content. Skipping.")
            continue
        post = generate_post(text, site)
        post_to_backendless(post)
        redis_client.sadd("seen_hashes", content_hash)


import sys

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Unhandled exception:", e)
        sys.exit(1)
    sys.exit(0)
