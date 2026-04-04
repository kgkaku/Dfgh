import requests
import json
import os

AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

def debug_tamasha():
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Cookie": USER_COOKIE if USER_COOKIE else "",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
        "X-Platform": "web",
        "Content-Type": "application/json",
        "Origin": "https://tamashaweb.com",
        "Referer": "https://tamashaweb.com/"
    }

    try:
        print("--- Sending Request ---")
        response = requests.post(url, headers=headers, json={}, timeout=20)
        
        print(f"Status Code: {response.status_code}")
        
        # সার্ভার থেকে আসা আসল টেক্সট প্রিন্ট করা (এখানেই আসল রহস্য লুকানো)
        raw_text = response.text
        print(f"Full Raw Response: {raw_text[:500]}") # প্রথম ৫০০ ক্যারেক্টার
        
        res_json = response.json()
        
        # আমরা এখানে সব ধরণের কি (keys) চেক করছি
        if "data" in res_json:
            data = res_json["data"]
            if isinstance(data, list):
                print(f"Found {len(data)} channels in 'data' list.")
            elif isinstance(data, dict):
                channels = data.get("channels", [])
                print(f"Found {len(channels)} channels in 'data -> channels'.")
            else:
                print("Data format is unusual.")
        else:
            print("Key 'data' not found in JSON response.")
            print(f"Available keys: {list(res_json.keys())}")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    debug_tamasha()
