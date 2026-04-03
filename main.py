import requests
import json
import os

AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

# হুবহু ব্রাউজারের মতো সিকিউরিটি হেডার
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Cookie": USER_COOKIE if USER_COOKIE else "",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "X-Platform": "web",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site"
}

def get_channels():
    # এন্ডপয়েন্ট ১ (v5)
    url_v5 = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    # ব্যাকআপ এন্ডপয়েন্ট ২ (v2 - এটি অনেক সময় বেশি কার্যকর)
    url_v2 = "https://web.jazztv.pk/alpha/api_gateway/v2/web/all-channels"
    
    for url in [url_v5, url_v2]:
        print(f"Trying to fetch from: {url}")
        try:
            response = requests.post(url, headers=HEADERS, json={}, timeout=20)
            if response.status_code == 200:
                res_data = response.json().get('data', [])
                # যদি ডাটা ডিকশনারি হয়, তবে 'channels' কি চেক করবে
                channels = res_data.get('channels', []) if isinstance(res_data, dict) else res_data
                if channels and len(channels) > 0:
                    return channels
            print(f"No data from {url}, trying next...")
        except:
            continue
    return []

def get_stream(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    try:
        res = requests.post(url, headers=HEADERS, json={"slug": slug, "type": "web"}, timeout=15)
        return res.json().get('data', {}).get('stream_url', "")
    except: return ""

if __name__ == "__main__":
    channels = get_channels()
    if channels:
        m3u = "#EXTM3U\n"
        count = 0
        for ch in channels:
            slug = ch.get('slug')
            title = ch.get('title') or ch.get('name')
            logo = ch.get('logo')
            if not slug: continue
            
            url = get_stream(slug)
            if url:
                m3u += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{title}\n'
                m3u += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
                m3u += f"{url}\n"
                count += 1
        
        with open("tamashaweb.m3u", "w", encoding="utf-8") as f: f.write(m3u)
        print(f"Success! Captured {count} channels.")
    else:
        print("CRITICAL: Server returned empty list on all endpoints.")
        print("Suggestion: Open Tamasha in Mises, Log out and Log in again, then get a fresh Token/Cookie.")
