
from flask import Flask
from threading import Thread
import time
from datetime import datetime, timezone
import requests
import os
import random
import hashlib
import json
import redis

# 🔧 Environment variables
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
APILAYER_API_KEY = os.getenv("APILAYER_API_KEY")
REDIS_URL = os.getenv("REDIS_URL")

# ⛓️ Redis client
redis_client = redis.Redis.from_url(REDIS_URL)

# 🌐 Sites considered heavy and need more delay
HEAVY_SITES = ["decrypt.co", "marketwatch.com", "bitcoinmagazine.com"]

# 🔁 Preferred API per domain
API_PREFERENCE = {
    "cointelegraph.com": "scraperapi",
    "psychologytoday.com": "scraperapi",
    "verywellmind.com": "scraperapi",
    "fool.com": "scraperapi",
}

# 🤖 Human-like User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
]

# 📄 Load target URLs
def post_to_backendless(post):
    try:
        # Backendless config
        APP_ID = os.getenv("BACKENDLESS_APP_ID")
        API_KEY = os.getenv("BACKENDLESS_API_KEY")  # REST API Key
        BASE_URL = f"https://api.backendless.com/{APP_ID}/{API_KEY}/data/Posts"

        # Payload
        payload = {
            "title": post["title"],
            "description": post["content"],
            "source": post["source"],
            "image": post["image"],
            "platform": post["platform"]
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
        
        if response.status_code < 300:
            print(f"✅ Sent to Backendless: {post['title']}")
        else:
            print(f"❌ Failed to send to Backendless: {response.status_code} → {response.text}")

    except Exception as e:
        print(f"❌ Exception sending to Backendless: {e}")

# 🧠 Generate post object
def generate_post(text, url, image_url=None):
    return {
        "title": "Betting Risk Exposed",
        "content": text[:1000],
        "source": url,
        "platform": "Blogspot",
        "image": image_url or ""
    }

# 🌐 Choose best headers
def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS)
    }

# 🛰️ Scraper methods
def extract_text_from_site(url):
    try:
        headers = get_headers()
        domain = url.split("//")[-1].split("/")[0].replace("www.", "")
        delay = 5 if domain in HEAVY_SITES else 1
        time.sleep(delay)

        preferred_api = API_PREFERENCE.get(domain)
        apis_to_try = ["apilayer", "scraperapi"] if not preferred_api else [preferred_api] + [a for a in ["apilayer", "scraperapi"] if a != preferred_api]

        for api_name in apis_to_try:
            try:
                print(f"🛰️ Trying: {api_name}")
                if api_name == "scraperapi":
                    proxy_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}"
                    response = requests.get(proxy_url, headers=headers, timeout=15)
                else:
                    response = requests.get(url, headers={"apikey": APILAYER_API_KEY, **headers}, timeout=15)

                if response.status_code == 403:
                    raise Exception("403 Forbidden")

                if response.status_code < 400:
                    text = response.text
                    return text, None
                else:
                    print(f"⚠️ Error with {api_name} → HTTP {response.status_code}")

            except Exception as e:
                print(f"⚠️ Error with {api_name} → {e}")

        # ☁️ Final fallback
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            text = scraper.get(url).text
            return text, None
        except Exception as e:
            print(f"❌ All scraping methods failed for {url}: {e}")
            return None

    except Exception as e:
        print(f"❌ Exception in extract_text_from_site → {e}")
        return None
        
# 📄 Load target URLs
def load_target_sites():
    try:
        with open("target_sites.txt", "r") as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(f"❌ Failed to load target sites: {e}")
        return []

# 🚀 Main runner
def main():
    TARGET_SITES = load_target_sites()
    for site in TARGET_SITES:
        try:
            head_response = requests.head(site, timeout=10)
            if head_response.status_code >= 400:
                print(f"🚫 HEAD check failed for {site} → {head_response.status_code}")
                continue
        except Exception as e:
            print(f"🚫 HEAD request error for {site} → {e}")
            continue

        if not site.startswith("http"):
            print(f"🚫 Skipping invalid URL: {site}")
            continue

        print("🔍 Scraping:", site)
        result = extract_text_from_site(site)
        if not result or not isinstance(result, tuple):
            continue

        text, image_url = result
        if not text:
            continue

        content_hash = hashlib.sha256(text.encode()).hexdigest()
        if redis_client.sismember("seen_hashes", content_hash):
            print("⏭️ Duplicate content. Skipping.")
            continue

        post = generate_post(text, site, image_url)
        post_to_backendless(post)
        redis_client.sadd("seen_hashes", content_hash)

# ------------------ Flask ------------------
from flask import Flask
app = Flask(__name__)

@app.route('/crawl-now', methods=["GET"])
def crawl_now():
    try:
        main()  # ← changed from Thread to direct call
        return "📡 Manual crawl triggered"
    except Exception as e:
        return f"❌ Failed to start manual crawl: {e}"

@app.route('/', methods=["GET"])
def home():
    return "🟢 NeuroX Crawler Running."

def loop_runner():
    try:
        while True:
            print(f"⏰ Auto Run: {datetime.now(timezone.utc).isoformat()}")
            main()
            print("🟢 Sleeping for 1 hour...\n")
            time.sleep(60 * 60)
    except Exception as e:
        print("❌ Error in loop:", e)

if __name__ == "__main__":
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=10000))
    flask_thread.daemon = True
    flask_thread.start()
    loop_runner()
