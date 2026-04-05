import requests
import json
import os
import re
from datetime import datetime

# ========== কনফিগারেশন ==========
HOME_API_URL = "https://www.btvlive.gov.bd/api/home"
# চ্যানেল কনফিগারেশন (আপনার দেওয়া ডাটা অনুযায়ী)
CHANNEL_API_CONFIG = {
    "BTV": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/BTV.json?id=BTV",
    "BTV News": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/BTV-News.json?id=BTV-News",
    "BTV Chattogram": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/BTV-Chattogram.json?id=BTV-Chattogram",
    "Sangsad Television": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/Sangsad-Television.json?id=Sangsad-Television"
}

def get_btv_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
        'referer': 'https://www.btvlive.gov.bd/'
    }
    
    final_channels = []
    print("🚀 Starting BTV Scraping...")

    for name, api_url in CHANNEL_API_CONFIG.items():
        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                page_props = data.get('pageProps', {})
                source_url = page_props.get('sourceURL', '')
                user_country = page_props.get('userCountry', 'BD')
                logo = page_props.get('channel', {}).get('poster', '')
                identifier = page_props.get('channel', {}).get('identifier', '')

                # userId এক্সট্রাক্ট করা (Regex ব্যবহার করে)
                match = re.search(r'/[^/]+/([^/]+)/index\.m3u8$', source_url)
                if match:
                    user_id = match.group(1)
                    # ফাইনাল স্ট্রিমিং লিঙ্ক তৈরি
                    stream_link = f"https://www.btvlive.gov.bd/live/{identifier}/{user_country}/{user_id}/index.m3u8"
                    
                    final_channels.append({
                        'name': name,
                        'logo': logo,
                        'url': stream_link
                    })
                    print(f"✅ Found: {name}")
        except Exception as e:
            print(f"❌ Error fetching {name}: {e}")

    # ফাইল তৈরি করা
    if final_channels:
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # M3U জেনারেশন
        m3u_content = f"#EXTM3U\n# Created by @kgkaku\n# Time: {update_time}\n# Total Channels: {len(final_channels)}\n\n"
        for ch in final_channels:
            m3u_content += f'#EXTINF:-1 tvg-logo="{ch["logo"]}", {ch["name"]}\n{ch["url"]}\n'
        
        with open('btv.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_content)

        # JSON জেনারেশন
        with open('btv.json', 'w', encoding='utf-8') as f:
            json.dump({"channels": final_channels, "credits": "@kgkaku", "updated": update_time}, f, indent=4)

        print(f"📊 Done! Total {len(final_channels)} channels saved.")

if __name__ == "__main__":
    get_btv_data()
