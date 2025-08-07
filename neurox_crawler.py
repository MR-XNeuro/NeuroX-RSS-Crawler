import os
from dotenv import load_dotenv
load_dotenv()
import cloudscraper
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# لیست سایت‌های سنگین که delay بیشتری لازم دارند
HEAVY_SITES = ["decrypt.co", "marketwatch.com", "bitcoinmagazine.com"]

# لیست سایت‌هایی که با یک API بهتر کار می‌کنند
API_PREFERENCE = {
    "cointelegraph.com": "scraperapi",
    "psychologytoday.com": "scraperapi",
    "verywellmind.com": "scraperapi",
    "fool.com": "scraperapi",
}

# User-Agent های واقعی و انسانی (موبایل + دسکتاپ Safari و Chrome)
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
]


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
    import requests
    import cloudscraper
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.replace("www.", "")

    # تعیین User-Agent تصادفی از لیست
    chosen_ua = random.choice(USER_AGENTS)

    headers_scraperapi = {
        "User-Agent": chosen_ua
    }

    headers_apilayer = {
        "Content-Type": "application/json",
        "apikey": APILAYER_API_KEY,
        "User-Agent": chosen_ua
    }

    # تأخیر داینامیک برای سایت‌های سنگین
    delay = random.uniform(4, 7) if domain in HEAVY_SITES else random.uniform(2, 4)

    # اگر ترجیح API مشخص شده باشد
    preferred_api = API_PREFERENCE.get(domain)

    apis = []
    if preferred_api == "scraperapi":
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
    elif preferred_api == "apilayer":
        apis = [
            {
                "name": "apilayer",
                "method": "POST",
                "url": "https://api.apilayer.com/scraper",
                "headers": headers_apilayer,
                "data": {"url": url},
                "is_json": True
            },
            {
                "name": "scraperapi",
                "method": "GET",
                "url": f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={url}",
                "headers": headers_scraperapi,
                "is_json": False
            }
        ]
    else:
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

    def extract_image_from_site(soup):
        img = soup.find("img")
        return img["src"] if img and img.has_attr("src") else None

    for api in apis:
        try:
            print(f"🛰️ Trying: {api['name']}")
            time.sleep(delay)
            if api["method"] == "GET":
                response = requests.get(api["url"], headers=api["headers"], timeout=15)
            else:
                response = requests.post(api["url"], headers=api["headers"], json=api.get("data", {}), timeout=15)
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            html = response.text if not api["is_json"] else response.json().get("content", "")
            soup = BeautifulSoup(html, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 80)
            image_url = extract_image_from_site(soup)
            return text.strip(), image_url
        except Exception:
            continue

    # fallback به cloudscraper در صورت شکست نهایی
    try:
        print("☁️ Fallback: Trying cloudscraper...")
        time.sleep(delay)
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers={"User-Agent": chosen_ua}, timeout=15)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "
".join(p.get_text() for p in paragraphs if len(p.get_text()) > 80)
        image_url = extract_image_from_site(soup)
        return text.strip(), image_url
    except Exception as e:
        print(f"❌ All scraping methods failed for {url}: {e}")
        return None, None

    headers_scraperapi = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0"
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
            print(f"🛰️ Trying: {api['name']}")
            time.sleep(random.uniform(2, 5))

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
            text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 80)
            image_url = extract_image_from_site(soup)
            return text.strip(), image_url

        except Exception as e:
            print(f"⚠️ Error with {api['name']} → {e}")
            continue

    # Fallback به cloudscraper
    try:
        print("☁️ Fallback: Trying cloudscraper...")
        time.sleep(random.uniform(2, 5))
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers_scraperapi, timeout=15)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 80)
        image_url = extract_image_from_site(soup)
        return text.strip(), image_url
    except Exception as e:
        print(f"❌ All scraping methods failed for {url}: {e}")
        return None, None


def load_promos(file_path="promo_texts.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines
    except Exception as e:
        print("⚠️ Failed to load promos:", e)
        return []

PROMO_LINES = load_promos()

def generate_post(text, source_url, image_url=""):
    promo = random.choice(PROMO_LINES) if PROMO_LINES else ""
    platform = random.choice(PLATFORMS)
    now = datetime.now(timezone.utc)
    return {
        "title": "Betting Risk Exposed",
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
    for site in TARGET_SITES:
        print("🔍 Scraping:", site)
        text, image_url = extract_text_from_site(site)
        if not text:
            continue
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        if redis_client.sismember("seen_hashes", content_hash):
            print("⏭️ Duplicate content. Skipping.")
            continue
        post = generate_post(text, site, image_url)
        post_to_backendless(post)
        redis_client.sadd("seen_hashes", content_hash)

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

if __name__ == "__main__":
    import threading

    def run_flask():
        app.run(host="0.0.0.0", port=10000)

    def loop_runner():
        try:
            while True:
                print(f"⏰ Auto Run: {datetime.now(timezone.utc).isoformat()}")
                main()
                print("🟢 Sleeping for 1 hour...\n")
                time.sleep(60 * 60)
        except Exception as e:
            print("❌ Error in loop:", e)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    loop_runner()
