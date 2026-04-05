import requests
import json
import time

# চ্যানেল লিস্ট
CHANNELS = {
    "KBS 1TV": "11",
    "KBS 2TV": "12",
    "KBS News 24": "I92",
    "KBS Drama": "N91",
    "KBS Joy": "N92",
    "KBS Life": "N93",
    "KBS Story": "N94",
    "KBS Kids": "N96",
    "KBS World": "14"
}

def get_live_url(ch_code):
    api_url = f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{ch_code}"
    
    # আপনার আপলোড করা ফাইল থেকে প্রাপ্ত সেশন ডাটা
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
        "Referer": "https://onair.kbs.co.kr/",
        "Origin": "https://onair.kbs.co.kr",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        # সেশন কুকি যা গিটহাবকে আপনার মোবাইলের মতো আচরণ করতে সাহায্য করবে
        "Cookie": "uuid=SMR_MEMBERS2026040510530492.38.135.93; STAT_WEBLOG_TOKEN=85285a5a-e3e9-432f-a035-5cedd798263e; _gid=GA1.3.1915578222.1775332594"
    }

    try:
        # ভেরিফিকেশন স্কিপ করতে verify=False ব্যবহার করা হয়েছে যদি SSL ইস্যু থাকে
        response = requests.get(api_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ {ch_code} এপিআই রেসপন্স কোড: {response.status_code}")
            return None
            
        data = response.json()
        
        # ডাটা স্ট্রাকচার থেকে সঠিক অবজেক্টটি খুঁজে বের করা
        target = None
        if isinstance(data, list) and len(data) > 0:
            target = data[0]
            if isinstance(target, list): target = target[0]
        elif isinstance(data, dict):
            target = data.get("channel_item", data)

        if target and isinstance(target, dict):
            url = target.get("service_url", target.get("main_url", ""))
            logo = target.get("channel_image", target.get("channel_thumb", ""))
            title = target.get("channel_title", "")
            
            # শুধুমাত্র ভিডিও লিংক (রেডিও বাদে) গ্রহণ করা
            if url and "m3u8" in url and "radio" not in url.lower():
                return {"url": url, "logo": logo, "name": title}
                
    except Exception as e:
        print(f"Error on {ch_code}: {e}")
    return None

def main():
    m3u_content = "#EXTM3U\n"
    json_output = []

    print("--- Starting Playlist Refresh using Browser Session ---")
    
    for display_name, code in CHANNELS.items():
        print(f"Fetching {display_name}...")
        info = get_live_url(code)
        
        if info:
            m3u_content += f'#EXTINF:-1 tvg-id="{code}" tvg-logo="{info["logo"]}",{display_name}\n'
            # VLC বা আইপিটিভি প্লেয়ারের জন্য হেডার
            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36\n'
            m3u_content += f'#EXTVLCOPT:http-referrer=https://onair.kbs.co.kr/\n'
            m3u_content += f"{info['url']}\n"
            
            json_output.append({
                "name": display_name,
                "url": info['url'],
                "logo": info['logo']
            })
            print(f"✅ Success: {display_name}")
        else:
            print(f"❌ Failed: {display_name} (Geo-restricted even with session)")
        
        time.sleep(2) # সার্ভার ব্লকিং এড়াতে সামান্য বিরতি

    # ফাইল আপডেট করা
    with open("kbsonair.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    with open("kbsonair.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=4, ensure_ascii=False)
    
    print("--- Refresh Completed ---")

if __name__ == "__main__":
    main()
