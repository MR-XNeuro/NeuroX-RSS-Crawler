import os
from dotenv import load_dotenv
load_dotenv()
import cloudscraper
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

import hashlib
import random
import redis
from redis.connection import SSLConnection
from datetime import datetime, timedelta, timezone
import time
from flask import Flask

# === تنظیمات ===
BACKENDLESS_APP_ID = os.getenv("BACKENDLESS_APP_ID")
BACKENDLESS_API_KEY = os.getenv("BACKENDLESS_API_KEY")
BACKENDLESS_API_URL = os.getenv("BACKENDLESS_API_URL")
BACKENDLESS_TABLE = "Posts"
API_URL = f"{BACKENDLESS_API_URL}/{BACKENDLESS_APP_ID}/{BACKENDLESS_API_KEY}/data/{BACKENDLESS_TABLE}"

TARGET_SITES_FILE = "target_sites.txt"
PLATFORMS = ["WordPress", "Blogspot", "Tumblr", "X"]

REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.Redis.from_url(REDIS_URL, connection_class=SSLConnection)

def load_target_sites():
    try:
        with open(TARGET_SITES_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print("⚠️ Failed to load target sites:", e)
        return []

def extract_image_from_site(soup):
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        return og_img["content"]
    twitter_img = soup.find("meta", property="twitter:image")
    if twitter_img and twitter_img.get("content"):
        return twitter_img["content"]
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return ""

def extract_text_from_site(url):
    import time
    import random
    import requests
    import os
    from bs4 import BeautifulSoup
    import cloudscraper

    SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
    APILAYER_API_KEY = os.getenv("APILAYER_API_KEY")

    if not SCRAPER_API_KEY or not APILAYER_API_KEY:
        print(f"❌ API keys not found. Skipping: {url}")
        return None, None, None

    headers_scraperapi = {
        "User-Agent": "Mozilla/5.0"
    }

    headers_apilayer = {
        "Content-Type": "application/json",
        "apikey": APILAYER_API_KEY
    }

    apis = [
        {
            "name": "scraperapi",
            "method": "GET",
            "url": f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={url}",
            "headers": headers_scraperapi,
            "is_json": False
        },
        {
            "name": "apilayer",
            "method": "POST",
            "url": "https://api.apilayer.com/scraper",
            "headers": headers_apilayer,
            "data": {"url": url},
            "is_json": True
        }
    ]

    random.shuffle(apis)

    for api in apis:
        try:
            print(f"🛰️ Trying: {api['name']} for {url}")
            time.sleep(random.uniform(1, 3))

            if api["method"] == "GET":
                response = requests.get(api["url"], headers=api["headers"], timeout=15)
            else:
                response = requests.post(
                    api["url"],
                    headers=api["headers"],
                    json=api.get("data", {}),
                    timeout=15
                )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            html = response.text if not api["is_json"] else response.json().get("content", "")
            soup = BeautifulSoup(html, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
            image_url = extract_image_from_site(soup)
            page_title = soup.title.string.strip() if soup.title else None
            return text.strip(), image_url, page_title

        except Exception as e:
            print(f"⚠️ Error with {api['name']} for {url} → {e}")
            continue

    # Fallback cloudscraper
    try:
        print(f"☁️ Fallback: Trying cloudscraper for {url}")
        time.sleep(random.uniform(1, 3))
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers_scraperapi, timeout=15)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
        image_url = extract_image_from_site(soup)
        page_title = soup.title.string.strip() if soup.title else None
        return text.strip(), image_url, page_title
    except Exception as e:
        print(f"❌ All scraping methods failed for {url}: {e}")
        return None, None, None

def load_promos(file_path="promo_texts.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines
    except Exception as e:
        print("⚠️ Failed to load promos:", e)
        return []

PROMO_LINES = load_promos()

platform_index = 0

def generate_post(text, source_url, image_url="", page_title=None):
    global platform_index
    promo = random.choice(PROMO_LINES) if PROMO_LINES else ""
    now = datetime.now(timezone.utc)

    # نوبتی بین پلتفرم‌ها
    platform = PLATFORMS[platform_index % len(PLATFORMS)]
    platform_index += 1

    if page_title:
        title = page_title[:250]
    else:
        title = text.split("\n")[0][:250]

    return {
        "title": title,
        "description": text + "\n\n" + promo,
        "imageUrl": image_url,
        "sourceUrl": source_url,
        "targetPlatform": platform,
        "scheduledAt": (now + timedelta(minutes=random.randint(5, 60))).strftime("%Y-%m-%d %H:%M:%S"),
        "status": "scheduled",
        "createdAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "updatedAt": now.strftime("%Y-%m-%d %H:%M:%S")
    }

def post_to_backendless(data):
    try:
        r = requests.post(API_URL, json=data)
        r.raise_for_status()
        print("✅ Sent to Backendless:", data["title"], "→", data["targetPlatform"])
    except Exception as e:
        print("❌ Failed to send post:", e)

def main():
    TARGET_SITES = load_target_sites()
    print(f"📄 Loaded {len(TARGET_SITES)} target sites")

    if not TARGET_SITES:
        print("⚠️ No target sites loaded.")
        return

    random.shuffle(TARGET_SITES)  # ترتیب تصادفی

    found_new = False
    for site in TARGET_SITES:
        print(f"🔍 Scraping: {site}")
        text, image_url, page_title = extract_text_from_site(site)
        if not text:
            print(f"⚠️ No text extracted from {site}")
            continue

        content_hash = hashlib.sha256((site + text).encode()).hexdigest()
        if redis_client.sismember("seen_hashes", content_hash):
            print(f"⏭️ Duplicate content for {site}. Skipping.")
            continue

        # ارسال فقط به WordPress
        post = generate_post(text, site, image_url, page_title)
        post["targetPlatform"] = "WordPress"
        post_to_backendless(post)

        redis_client.sadd("seen_hashes", content_hash)
        found_new = True
        break  # بعد از اولین مطلب جدید، توقف

    if not found_new:
        print("⚠️ No new content found in any target site.")

# === Flask Setup ===
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 NeuroX Crawler Running."

from threading import Thread

@app.route('/crawl-now', methods=["GET"])
def trigger_crawler():
    print("📡 Manual crawl triggered")

    def async_crawl():
        try:
            main()
            print("✅ Manual crawl completed")
        except Exception as e:
            print("❌ Error during manual crawl:", e)

    Thread(target=async_crawl).start()
    return "✅ Crawling started!"


def loop_runner():
    try:
        while True:
            print(f"⏰ Auto Run: {datetime.now(timezone.utc).isoformat()}")
            main()
            sleep_time = 60 * 60  # هر ۱ ساعت
            time.sleep(sleep_time)
    except Exception as e:
        print("❌ Error in loop:", e)

if __name__ == "__main__":
    import threading

    def run_flask():
        app.run(host="0.0.0.0", port=10000)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    loop_runner()
