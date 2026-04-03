import requests
import json
import os

# GitHub Secrets থেকে টোকেন সংগ্রহ
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/"
}

def get_all_channels():
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            print(f"Error fetching channels: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

def get_stream_url(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    payload = {
        "slug": slug,
        "type": "web"
    }
    try:
        # এখানে POST রিকোয়েস্ট পাঠানো হচ্ছে স্ট্রিমিং ইউআরএল এর জন্য
        response = requests.post(url, headers=HEADERS, data=payload)
        if response.status_code == 200:
            return response.json().get('data', {}).get('stream_url', "")
    except:
        return ""
    return ""

def generate_files(channels):
    m3u_content = "#EXTM3U\n"
    json_data = []

    for ch in channels:
        name = ch.get('title', 'Unknown')
        logo = ch.get('logo', '')
        slug = ch.get('slug', '')
        
        print(f"Processing: {name}")
        stream_url = get_stream_url(slug)

        if stream_url:
            # Extvlcopt ফরম্যাটে M3U তৈরি
            m3u_content += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer={HEADERS["Referer"]}\n'
            m3u_content += f"{stream_url}\n"

            # JSON ডাটা তৈরি
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
        print("AUTH_TOKEN not found in environment variables!")
    else:
        channels = get_all_channels()
        if channels:
            generate_files(channels)
            print("Successfully generated tamashaweb.m3u and tamashaweb.json")
        else:
            print("No channels found.")
