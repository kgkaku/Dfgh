#!/usr/bin/env python3
"""
Toffee Live TV + Radio Playlist Generator
- সব রেল থেকে লাইভ চ্যানেল সংগ্রহ
- রেডিও আলাদা এন্ডপয়েন্ট
- অটো টোকেন রিফ্রেশ
"""

import json
import os
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ========== কনফিগারেশন (হার্ডকোডেড nonce/hash) ==========
HARDCODED_NONCE = "GAMRZISrXAXcZAYeTdtTTAOhoHB8-6g2OSZjYbChvCM%3D%0A"
HARDCODED_HASH = "638a979f244384bd334d9462e0fa4fd4c2a69f8a0ec4aa6c4694b3faa0271b31ef4a86310aaa136642a49418afd5cad951a300a8d395fe3bed9f71c46c4aaf5843fc7e527567e264f199ca9f928b636e5776478d98a209479ad3be7fe5de2103c517bffd1680c137187827dcce756e8ef1e28aca05e86694092e8e793a45a32f55d11415fc62d556ac99344797b00a2e"
HARDCODED_DEVICE_ID = "58c6e0cde782de43"

DEVICE_REGISTER_URL = "https://prod-services.toffeelive.com/sms/v1/device/register"
TOKEN_REFRESH_URL = "https://prod-services.toffeelive.com/v1/token/refresh"
CONTENT_BASE = "https://content-prod.services.toffeelive.com/toffee/BD/DK/android-mobile"
PLAYBACK_BASE = "https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/android-mobile/playback"
HOME_VIEW_URL = f"{CONTENT_BASE}/view/home"
RADIO_ENDPOINT = f"{CONTENT_BASE}/rail/generic/editorial-dynamic?filters=v_type:channels;subType:radio"

TOKEN_FILE = "toffee_token.json"

COMMON_HEADERS = {
    "User-Agent": "okhttp/5.1.0",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

# গ্রুপ ম্যাপিং (জেনার বা রেলের টাইটেল অনুযায়ী)
GENRE_GROUP_MAP = {
    "Sports": "Sports Channels",
    "News": "News Channels",
    "Movie": "Movie Channels",
    "Entertainment": "Entertainment Channels",
    "Infotainment": "Infotainment",
    "Kids": "Kids",
    "Music": "Music Channels"
}
DEFAULT_GROUP = "Live TV"

# ========== টোকেন ব্যবস্থাপনা (পূর্বের মতো) ==========
def register_device() -> Optional[Dict]:
    url = f"{DEVICE_REGISTER_URL}?nonce={HARDCODED_NONCE}&hash={HARDCODED_HASH}"
    payload = {
        "device_id": HARDCODED_DEVICE_ID,
        "type": "mobile",
        "provider": "toffee",
        "os": "android",
        "country": "IN",
        "app_version": "8.8.0",
        "os_version": "7.1.2"
    }
    headers = {
        "Host": "prod-services.toffeelive.com",
        "Content-Type": "application/json; charset=utf-8",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/5.1.0"
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Device registration failed: {resp.status_code}")
            return None
        data = resp.json()
        if data.get("success") and "data" in data:
            return {
                "access_token": data["data"]["access"],
                "refresh_token": data["data"]["refresh"],
                "access_expiry": data["data"]["access_expiry"],
                "refresh_expiry": data["data"]["refresh_expiry"],
                "device_id": HARDCODED_DEVICE_ID
            }
    except Exception as e:
        print(f"❌ Registration error: {e}")
    return None

def refresh_access_token(refresh_token: str) -> Optional[str]:
    headers = {"Authorization": f"Bearer {refresh_token}", "User-Agent": "okhttp/5.1.0"}
    try:
        resp = requests.post(TOKEN_REFRESH_URL, headers=headers, json={}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if "access_token" in data:
                return data["access_token"]
            elif "data" in data and "access" in data["data"]:
                return data["data"]["access"]
    except:
        pass
    return None

def load_token() -> Optional[Dict]:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def save_token(token_data: Dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

def get_valid_access_token() -> Optional[str]:
    token_data = load_token()
    if not token_data:
        print("🔄 No saved token, registering device...")
        token_data = register_device()
        if token_data:
            save_token(token_data)
            return token_data["access_token"]
        return None
    access_expiry = token_data.get("access_expiry")
    if access_expiry and datetime.fromtimestamp(access_expiry) - datetime.now() < timedelta(days=1):
        print("🔄 Refreshing access token...")
        new_access = refresh_access_token(token_data["refresh_token"])
        if new_access:
            token_data["access_token"] = new_access
            save_token(token_data)
            return new_access
        else:
            print("⚠️ Refresh failed, re-registering...")
            token_data = register_device()
            if token_data:
                save_token(token_data)
                return token_data["access_token"]
    return token_data["access_token"]

# ========== চ্যানেল সংগ্রহের ফাংশন ==========
def get_home_json(access_token: str) -> Optional[Dict]:
    headers = {"Authorization": f"Bearer {access_token}", **COMMON_HEADERS}
    try:
        resp = requests.get(HOME_VIEW_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"❌ Home view error: {e}")
    return None

def fetch_rail_page(rail_hash: str, page: int, access_token: str) -> Optional[List[Dict]]:
    url = f"{CONTENT_BASE}/rail/generic/editorial-dynamic/{rail_hash}?page={page}"
    headers = {"Authorization": f"Bearer {access_token}", **COMMON_HEADERS}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("list", [])
    except:
        pass
    return None

def get_all_live_channels_from_home(access_token: str) -> List[Dict]:
    """সব রেল থেকে subType Live_TV বা Live_Event সংগ্রহ করে"""
    home = get_home_json(access_token)
    if not home:
        return []
    all_channels = []
    rails = home.get("rails", {}).get("list", [])
    for rail in rails:
        api_path = rail.get("apiPath")
        if not api_path or not api_path.startswith("rail/generic/editorial-dynamic/"):
            continue
        rail_hash = api_path.split("/")[3]
        page = 1
        while True:
            items = fetch_rail_page(rail_hash, page, access_token)
            if not items:
                break
            # ফিল্টার: শুধু লাইভ টিভি বা লাইভ ইভেন্ট
            live_items = [ch for ch in items if ch.get("subType") in ("Live_TV", "Live_Event")]
            all_channels.extend(live_items)
            print(f"   Rail {rail_hash[:8]}... page {page}: {len(live_items)} live (total {len(all_channels)})")
            page += 1
            if page > 20:
                break
    return all_channels

def get_radio_channels(access_token: str) -> List[Dict]:
    headers = {"Authorization": f"Bearer {access_token}", **COMMON_HEADERS}
    try:
        resp = requests.get(RADIO_ENDPOINT, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("list", [])
    except Exception as e:
        print(f"❌ Radio fetch error: {e}")
    return []

def get_radio_stream_url(radio_ch: Dict) -> Optional[str]:
    if "stream_url" in radio_ch:
        return radio_ch["stream_url"]
    media_list = radio_ch.get("media", [])
    for media in media_list:
        if "url" in media:
            return media["url"]
    return None

def get_playback_data(channel_id: str, access_token: str) -> Optional[Dict]:
    url = f"{PLAYBACK_BASE}/{channel_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "okhttp/5.1.0"
    }
    try:
        resp = requests.post(url, headers=headers, json={}, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Playback failed {channel_id}: {resp.status_code}")
            return None
        data = resp.json()
        stream_url = None
        try:
            stream_url = data["playbackDetails"]["data"][0]["url"]
        except:
            stream_url = data.get("stream_url")
        if not stream_url:
            return None
        cookie = None
        if "set-cookie" in resp.headers:
            match = re.search(r'(Edge-Cache-Cookie=[^;]+)', resp.headers["set-cookie"])
            if match:
                cookie = match.group(1)
        return {"stream_url": stream_url, "cookie": cookie}
    except Exception as e:
        print(f"❌ Playback error {channel_id}: {e}")
        return None

def get_logo(channel: Dict) -> str:
    images = channel.get("images", [])
    for img in images:
        if img.get("ratio") == "1:1":
            path = img.get("path", "")
            if path:
                if path.startswith("http"):
                    return path
                else:
                    return f"https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/{path}"
    if images:
        best = min(images, key=lambda x: x.get("width", 9999))
        path = best.get("path", "")
        if path:
            if path.startswith("http"):
                return path
            else:
                return f"https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/{path}"
    return ""

def get_group_from_genres(genres: List[str]) -> str:
    for genre in genres:
        for key, group in GENRE_GROUP_MAP.items():
            if key.lower() in genre.lower():
                return group
    return DEFAULT_GROUP

def escape_m3u_field(text: str) -> str:
    return f'"{text}"' if ',' in text else text

def main():
    print("🔄 Toffee Playlist Generator (All Rails + Radio)")

    access_token = get_valid_access_token()
    if not access_token:
        print("❌ No access token. Exiting.")
        return
    print("✅ Access token ready")

    # সব লাইভ চ্যানেল সংগ্রহ (সব রেল থেকে)
    print("\n📺 Fetching live channels from all rails...")
    live_channels = get_all_live_channels_from_home(access_token)
    print(f"✅ Total live channels found: {len(live_channels)}")

    # রেডিও চ্যানেল
    print("\n📻 Fetching radio channels...")
    radio_channels = get_radio_channels(access_token)
    print(f"✅ Radio channels found: {len(radio_channels)}")

    # m3u লাইন তৈরি
    m3u_lines = ["#EXTM3U"]
    json_output = {"generated": datetime.utcnow().isoformat(), "channels": []}

    # প্রক্রিয়াকরণ লাইভ চ্যানেল
    for idx, ch in enumerate(live_channels, 1):
        title = ch.get("title", "Unknown")
        ch_id = ch.get("id")
        if not ch_id:
            continue
        logo = get_logo(ch)
        genres = ch.get("genres", [])
        group = get_group_from_genres(genres)
        playback = get_playback_data(ch_id, access_token)
        if not playback or not playback["stream_url"]:
            print(f"⚠️ No stream for {title}")
            continue
        m3u_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}" tvg-name="{escape_m3u_field(title)}", {title}')
        m3u_lines.append('#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
        if playback.get("cookie"):
            m3u_lines.append(f'#EXTHTTP:{{"cookie":"{playback["cookie"]}"}}')
        m3u_lines.append(playback["stream_url"])
        m3u_lines.append("")
        json_output["channels"].append({
            "type": "live_tv",
            "title": title,
            "id": ch_id,
            "group": group,
            "logo": logo,
            "stream_url": playback["stream_url"],
            "cookie": playback.get("cookie")
        })
        print(f"✅ [{idx}/{len(live_channels)}] {title} → {group}")

    # রেডিও
    for idx, ch in enumerate(radio_channels, 1):
        title = ch.get("title", "Unknown")
        stream_url = get_radio_stream_url(ch)
        if not stream_url:
            print(f"⚠️ No stream URL for radio {title}")
            continue
        logo = get_logo(ch)
        group = "Radios"
        m3u_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}" tvg-name="{escape_m3u_field(title)}", {title}')
        m3u_lines.append('#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
        m3u_lines.append(stream_url)
        m3u_lines.append("")
        json_output["channels"].append({
            "type": "radio",
            "title": title,
            "group": group,
            "logo": logo,
            "stream_url": stream_url
        })
        print(f"✅ [{idx}/{len(radio_channels)}] Radio: {title}")

    with open("toffee.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    with open("toffee.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Success! {len(json_output['channels'])} channels written.")

if __name__ == "__main__":
    main()
