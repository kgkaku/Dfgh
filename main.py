import requests
import json
import os

# GitHub Secrets থেকে টোকেন সংগ্রহ
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Platform": "web"
}

def get_all_channels():
    # আপনার লগ অনুযায়ী এটি GET রিকোয়েস্ট
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            data = response.json().get('data', [])
            # অনেক সময় ডাটা সরাসরি লিস্ট না হয়ে 'channels' কি-র ভেতর থাকে
            if isinstance(data, dict):
                return data.get('channels', [])
            return data
        else:
            print(f"Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

def get_stream_url(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    # স্যাম্পল কার্ল অনুযায়ী এটি JSON পেলোড হতে পারে
    payload = {
        "slug": slug,
        "type": "web"
    }
    try:
        # payload ডাটা হিসেবে না পাঠিয়ে json হিসেবে পাঠানো হচ্ছে (বেশি নির্ভরযোগ্য)
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', {}).get('stream_url', "")
    except:
        return ""
    return ""

def generate_files(channels):
    m3u_content = "#EXTM3U\n"
    json_data = []

    for ch in channels:
        name = ch.get('title') or ch.get('name') or 'Unknown'
        logo = ch.get('logo') or ch.get('image_url') or ''
        slug = ch.get('slug') or ''
        
        if not slug: continue
        
        print(f"Processing: {name}")
        stream_url = get_stream_url(slug)

        if stream_url:
            m3u_content += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={HEADERS["Referer"]}\n'
            m3u_content += f"{stream_url}\n"
            
            json_data.append({
                "name": name,
                "logo": logo,
                "url": stream_url
            })

    # ফাইল সেভ করা
    with open("tamashaweb.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    with open("tamashaweb.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

if __name__ == "__main__":
    if not AUTH_TOKEN:
        print("AUTH_TOKEN missing!")
    else:
        channels = get_all_channels()
        if channels and len(channels) > 0:
            generate_files(channels)
            print(f"Successfully processed {len(channels)} channels.")
        else:
            # ফাইল না পেলে গিটহাবের এরর এড়াতে ডামি ফাইল
            with open("tamashaweb.m3u", "w") as f: f.write("#EXTM3U\n")
            with open("tamashaweb.json", "w") as f: f.write("[]")
            print("No channels were found. Please check AUTH_TOKEN.")
