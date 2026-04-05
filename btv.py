import requests
import json
import re
from datetime import datetime

# সরাসরি ওয়েবসাইট থেকে কারেন্ট বিল্ড আইডি খুঁজে বের করার ফাংশন
def get_build_id():
    url = "https://www.btvlive.gov.bd/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # স্ক্রিপ্ট ট্যাগ থেকে buildId খুঁজে বের করা
        match = re.search(r'"buildId":"(.*?)"', response.text)
        if match:
            return match.group(1)
    except:
        pass
    return "wr5BMimBGS-yN5Rc2tmam" # ফলব্যাক আইডি

def get_btv_data():
    build_id = get_build_id()
    print(f"🚀 Using Build ID: {build_id}")
    
    channels_to_fetch = {
        "BTV": "BTV",
        "BTV News": "BTV-News",
        "BTV Chattogram": "BTV-Chattogram",
        "Sangsad Television": "Sangsad-Television"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K)',
        'referer': 'https://www.btvlive.gov.bd/'
    }
    
    final_channels = []

    for display_name, slug in channels_to_fetch.items():
        api_url = f"https://www.btvlive.gov.bd/_next/data/{build_id}/channel/{slug}.json?id={slug}"
        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                page_props = data.get('pageProps', {})
                source_url = page_props.get('sourceURL', '')
                user_country = page_props.get('userCountry', 'BD')
                logo = page_props.get('channel', {}).get('poster', '')
                identifier = page_props.get('channel', {}).get('identifier', '')

                match = re.search(r'/[^/]+/([^/]+)/index\.m3u8$', source_url)
                if match:
                    user_id = match.group(1)
                    stream_link = f"https://www.btvlive.gov.bd/live/{identifier}/{user_country}/{user_id}/index.m3u8"
                    
                    final_channels.append({
                        'name': display_name,
                        'logo': logo,
                        'url': stream_link
                    })
                    print(f"✅ Captured: {display_name}")
        except Exception as e:
            print(f"❌ Failed {display_name}: {e}")

    if final_channels:
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # M3U আউটপুট উইথ ক্রেডিট
        m3u_header = (
            f"#EXTM3U\n"
            f"# Created by @kgkaku\n"
            f"# Time: {update_time}\n"
            f"# Total Channels: {len(final_channels)}\n\n"
        )
        
        m3u_body = ""
        for ch in final_channels:
            m3u_body += f'#EXTINF:-1 tvg-logo="{ch["logo"]}", {ch["name"]}\n{ch["url"]}\n'
        
        with open('btv.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_header + m3u_body)

        with open('btv.json', 'w', encoding='utf-8') as f:
            json.dump({"channels": final_channels, "credits": "@kgkaku", "updated": update_time}, f, indent=4)

        print(f"📊 Process Completed. {len(final_channels)} channels added.")

if __name__ == "__main__":
    get_btv_data()
