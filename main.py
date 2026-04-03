import cloudscraper
import json
import os

AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

def get_data():
    # Cloudscraper ব্রাউজারের সিকিউরিটি দেয়াল ভেঙে দেয়
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
    
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Cookie": USER_COOKIE if USER_COOKIE else "",
        "X-Platform": "web",
        "Referer": "https://tamashaweb.com/",
        "Origin": "https://tamashaweb.com/"
    }

    try:
        print("Bypassing security layers...")
        response = scraper.post(url, headers=headers, json={}, timeout=25)
        
        if response.status_code == 200:
            data = response.json().get('data', [])
            return data if isinstance(data, list) else data.get('channels', [])
        else:
            print(f"Failed again. Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    channels = get_data()
    if channels:
        m3u = "#EXTM3U\n"
        for ch in channels:
            m3u += f"#EXTINF:-1,{ch.get('title')}\n{ch.get('slug')}\n" # সিম্পল টেস্ট
        with open("tamashaweb.m3u", "w") as f: f.write(m3u)
        print(f"Final Success! Found {len(channels)} channels.")
    else:
        print("Still Empty. Tamasha has successfully blocked GitHub entirely.")
