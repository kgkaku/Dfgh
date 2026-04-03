import requests
import json
import os

# গিটহাব থেকে ডাটা রিড করা
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

def start_sync():
    # ১. টোকেন চেক
    if not AUTH_TOKEN or not USER_COOKIE:
        print("CRITICAL: AUTH_TOKEN or USER_COOKIE is empty in Environment Variables!")
        return

    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Cookie": USER_COOKIE,
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
        "X-Platform": "web",
        "Content-Type": "application/json"
    }

    print("Sending request to Tamasha servers...")
    try:
        response = requests.post(url, headers=headers, json={}, timeout=20)
        
        if response.status_code == 200:
            channels = response.json().get('data', [])
            if channels:
                print(f"Success! Found {len(channels)} channels.")
                # এখানে ফাইল সেভ করার লজিক...
                with open("tamashaweb.m3u", "w") as f: f.write("#EXTM3U\n") # টেস্ট ফাইল
                return
            else:
                print("Server returned 200 but channel list is EMPTY.")
        else:
            print(f"Server Error: {response.status_code}")
            print(f"Response: {response.text[:100]}")
            
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    start_sync()
