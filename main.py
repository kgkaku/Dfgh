import requests
import json
import os

# GitHub Secrets থেকে টোকেন সংগ্রহ
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

# ব্রাউজারের হুবহু হেডার কপি করা হয়েছে আপনার কার্ল কমান্ড থেকে
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "Accept": "application/json, text/plain, */*",
    "X-Platform": "web",
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-mobile": "?1"
}

def get_all_channels():
    # এপিআই এন্ডপয়েন্ট
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    
    try:
        # ৪৪ ও ৪৫ রানের এরর এড়াতে আমরা সেশন ব্যবহার করব
        session = requests.Session()
        
        # প্রথমে একটি GET রিকোয়েস্ট (headers সহ)
        response = session.get(url, headers=HEADERS, timeout=15)
        
        # যদি ৪৪/৪৫ রানের মতো এরর দেয়, তবে POST ট্রাই করবে (JSON বডি সহ)
        if response.status_code == 405 or response.status_code == 404:
            response = session.post(url, headers=HEADERS, json={}, timeout=15)
            
        if response.status_code == 200:
            res_json = response.json()
            # ডাটা ফিল্ড চেক করা
            channels = res_json.get('data', [])
            if isinstance(channels, dict):
                return channels.get('channels', [])
            return channels
        else:
            print(f"Server responded with code: {response.status_code}")
            print(f"Raw Response: {response.text[:200]}") # এরর ডিবাগ করার জন্য
            return []
    except Exception as e:
        print(f"Request Exception: {e}")
        return []

def get_stream_url(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    payload = {"slug": slug, "type": "web"}
    try:
        # এই রিকোয়েস্টটি অবশ্যই JSON ফরম্যাটে হতে হবে
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
        
        print(f"Capturing: {name}")
        stream_url = get_stream_url(slug)

        if stream_url:
            # Extvlcopt ফরম্যাট বজায় রাখা হয়েছে
            m3u_content += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={HEADERS["Referer"]}\n'
            m3u_content += f"{stream_url}\n"
            
            json_data.append({"name": name, "logo": logo, "url": stream_url})

    # ফাইলগুলো রাইট করা
    with open("tamashaweb.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    with open("tamashaweb.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

if __name__ == "__main__":
    if not AUTH_TOKEN or len(AUTH_TOKEN) < 20:
        print("CRITICAL: AUTH_TOKEN is invalid or missing in Secrets!")
    else:
        channels = get_all_channels()
        if channels:
            generate_files(channels)
            print(f"Success! Processed {len(channels)} channels.")
        else:
            # ডামি ফাইল যাতে commit ফেইল না করে
            with open("tamashaweb.m3u", "w") as f: f.write("#EXTM3U\n")
            with open("tamashaweb.json", "w") as f: f.write("[]")
            print("No channels found. Token might be expired.")
