import requests
import json

# চ্যানেল লিস্ট
CHANNELS = {
    "KBS 1TV": "11",
    "KBS 2TV": "12",
    "KBS Drama": "N91",
    "KBS Joy": "N92",
    "KBS Life": "N93",
    "KBS Story": "N94",
    "KBS Kids": "N96",
    "KBS World": "14",
    "KBS News 24": "I92"
}

def get_live_url(ch_code):
    api_url = f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{ch_code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
        "Referer": "https://onair.kbs.co.kr/",
        "Origin": "https://onair.kbs.co.kr",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        data = response.json()
        
        # এপিআই যদি সরাসরি লিস্ট পাঠায় তবে প্রথম এলিমেন্টটি নেব
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
        elif isinstance(data, dict):
            # যদি ডিকশনারি হয় তবে 'channel_item' চেক করব
            item = data.get("channel_item", data)
        else:
            return None

        stream_url = item.get("service_url", "")
        logo = item.get("channel_image", "")
        # যদি চ্যানেল ইমেজ না থাকে তবে থাম্বনেইল দেখব
        if not logo:
            logo = item.get("channel_thumb", "")
        
        title = item.get("channel_title", "")
        
        return {"url": stream_url, "logo": logo, "name": title}
    except Exception as e:
        print(f"Error parsing {ch_code}: {e}")
        return None

def main():
    m3u_content = "#EXTM3U\n"
    json_data = []

    for display_name, code in CHANNELS.items():
        print(f"Fetching {display_name}...")
        info = get_live_url(code)
        
        if info and info['url']:
            final_name = info['name'] if info['name'] else display_name
            # M3U Format
            m3u_content += f'#EXTINF:-1 tvg-name="{final_name}" tvg-logo="{info["logo"]}",{final_name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K)\n'
            m3u_content += f'#EXTVLCOPT:http-referrer=https://onair.kbs.co.kr/\n'
            m3u_content += f"{info['url']}\n"
            
            # JSON Format
            json_data.append({
                "name": final_name,
                "logo": info["logo"],
                "url": info["url"]
            })
            print(f"Successfully fetched {final_name}")
        else:
            print(f"Failed to get URL for {display_name}")

    # ফাইল সেভ করা
    with open("kbsonair.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    with open("kbsonair.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
