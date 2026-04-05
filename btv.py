import requests
import json
import re
import os
from datetime import datetime

# বিটিভি এর সিডিএন এবং মেইন ইউআরএল
BASE_URL = "https://www.btvlive.gov.bd"
BTV_NEWS_POSTER = "https://d38ll44lbmt52p.cloudfront.net/cms/channel_poster/1735648543857_Poster.jpg"

def get_build_id():
    """স্বয়ংক্রিয়ভাবে লেটেস্ট Build ID খুঁজে বের করার ফাংশন"""
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K)'}
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        match = re.search(r'"buildId":"(.*?)"', response.text)
        if match:
            return match.group(1)
    except:
        pass
    return "wr5BMimBGS-yN5Rc2tmam"

def fetch_and_generate():
    build_id = get_build_id()
    print(f"🚀 Current Build ID: {build_id}")

    channels_to_fetch = {
        "BTV": "BTV",
        "BTV News": "BTV-News",
        "BTV Chattogram": "BTV-Chattogram",
        "Sangsad Television": "Sangsad-Television"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K)',
        'referer': BASE_URL,
        'accept': 'application/json'
    }

    final_channels = []

    for display_name, slug in channels_to_fetch.items():
        api_url = f"{BASE_URL}/_next/data/{build_id}/channel/{slug}.json?id={slug}"
        
        try:
            resp = requests.get(api_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                json_data = resp.json()
                page_props = json_data.get('pageProps', {})
                channel_info = page_props.get('channel', {})
                
                # ১. লোগো/পোস্টার সেটআপ
                if display_name == "BTV News":
                    # বিটিভি নিউজ এর জন্য আপনার দেওয়া নির্দিষ্ট লিংক
                    logo_url = BTV_NEWS_POSTER
                else:
                    # বাকিদের জন্য সরাসরি poster সেকশন থেকে
                    raw_poster = channel_info.get('poster', '')
                    if raw_poster:
                        # যদি সিডিএন লিংক না থাকে তবে ডোমেইন যোগ করা হবে
                        if raw_poster.startswith('http'):
                            logo_url = raw_poster
                        else:
                            logo_url = f"https://d38ll44lbmt52p.cloudfront.net/{raw_poster.lstrip('/')}"
                    else:
                        logo_url = ""

                # ২. স্ট্রিম ইউআরএল প্রসেসিং
                source_url = page_props.get('sourceURL', '')
                identifier = channel_info.get('identifier', slug)
                user_country = "BD" 

                match = re.search(r'/[^/]+/([^/]+)/index\.m3u8$', source_url)
                if match:
                    user_id = match.group(1)
                    stream_link = f"{BASE_URL}/live/{identifier}/{user_country}/{user_id}/index.m3u8"
                    
                    final_channels.append({
                        'name': display_name,
                        'id': identifier,
                        'logo': logo_url,
                        'url': stream_link
                    })
                    print(f"✅ Fetched: {display_name}")
        except Exception as e:
            print(f"❌ Error in {display_name}: {e}")

    if final_channels:
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # M3U ফাইল তৈরি (ক্রেডিট + লোগো + কান্ট্রি কোড)
        m3u_header = (
            f"#EXTM3U\n"
            f"# Created by @kgkaku\n"
            f"# Time: {update_time}\n"
            f"# Total Channels: {len(final_channels)}\n\n"
        )
        
        m3u_body = ""
        for ch in final_channels:
            m3u_body += f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" tvg-country="BD", {ch["name"]}\n{ch["url"]}\n\n'
        
        with open('btv.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_header + m3u_body)

        with open('btv.json', 'w', encoding='utf-8') as f:
            json.dump({
                "credits": "@kgkaku",
                "last_updated": update_time,
                "total_channels": len(final_channels),
                "channels": final_channels
            }, f, indent=4, ensure_ascii=False)

        print(f"📊 Success! btv.m3u updated by @kgkaku")

if __name__ == "__main__":
    fetch_and_generate()
