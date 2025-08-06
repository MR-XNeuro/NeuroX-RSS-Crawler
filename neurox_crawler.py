import os
from dotenv import load_dotenv
load_dotenv()


import requests
from bs4 import BeautifulSoup
import hashlib
import json
import random
import time
from datetime import datetime, timedelta

# === تنظیمات ===
BACKENDLESS_APP_ID = os.getenv("BACKENDLESS_APP_ID")
BACKENDLESS_API_KEY = os.getenv("BACKENDLESS_API_KEY")
BACKENDLESS_TABLE = "Posts"
API_URL = f"{os.getenv("BACKENDLESS_API_URL")}/{BACKENDLESS_APP_ID}/{BACKENDLESS_API_KEY}/data/{BACKENDLESS_TABLE}"

TARGET_SITES = [
    "https://www.example.com/articles/gambling-risks",
    "https://www.example.org/blog/the-dangers-of-betting"
]

SEEN_HASHES_FILE = "seen_hashes.json"

def load_seen_hashes():
    try:
        with open(SEEN_HASHES_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen_hashes(hashes):
    with open(SEEN_HASHES_FILE, "w") as f:
        json.dump(list(hashes), f)

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


# --- Load promotional texts ---
def load_promos(file_path="promo_texts.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines
    except Exception as e:
        print("⚠️ Failed to load promos:", e)
        return []

PROMO_LINES = load_promos()


    promo_text = "\n\n🔗 Learn how to defeat betting systems with the NeuroX AI bot:\nhttps://mr-xneuro.github.io/neurobet-demo/"
    return {
        "title": "Betting Risk Exposed",
        "description": text + promo_text,
        "imageUrl": "",
        "targetPlatform": "WordPress",
        "scheduledAt": (datetime.utcnow() + timedelta(minutes=random.randint(5, 60))).strftime("%Y-%m-%d %H:%M:%S"),
        "status": "scheduled",
        "createdAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "updatedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

def post_to_backendless(data):
    try:
        r = requests.post(API_URL, json=data)
        r.raise_for_status()
        print("✅ Sent:", data["title"])
    except Exception as e:
        print("❌ Failed to send post:", e)

def main():
    seen = load_seen_hashes()
    for site in TARGET_SITES:
        print("🔍 Scraping:", site)
        text = extract_text_from_site(site)
        if not text:
            continue

        content_hash = hashlib.sha256(text.encode()).hexdigest()
        if content_hash in seen:
            print("⏭️ Duplicate content. Skipping.")
            continue

        post = generate_post(text, site)
        post_to_backendless(post)
        seen.add(content_hash)

    save_seen_hashes(seen)

if __name__ == "__main__":
    main()
