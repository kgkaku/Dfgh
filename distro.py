import json
import requests
from datetime import datetime
import time
import random
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.distro.tv/",
    "Origin": "https://www.distro.tv",
    "Connection": "keep-alive",
}

def master_to_manifest(master_url):
    """
    Convert master.m3u8 URL to working manifest URL
    Example: /v1/master/.../channel-name/master.m3u8?params
    becomes: /v1/manifest/.../channel-name/uuid/0.m3u8
    """
    if not master_url or "/master/" not in master_url:
        return None
    
    # Remove query parameters
    base_url = master_url.split("?")[0]
    
    # Extract path between /master/ and /master.m3u8
    match = re.search(r'/master/(.+?)/[^/]+\.m3u8$', base_url)
    if not match:
        return None
    
    channel_path = match.group(1)
    
    # Generate random UUID for manifest
    import uuid
    manifest_id = str(uuid.uuid4())
    
    # Construct manifest URL (try different resolutions)
    manifest_url = base_url.replace("/master/", f"/manifest/{channel_path}/{manifest_id}/0.m3u8")
    
    return manifest_url

def extract_master_url(show_data):
    """Extract master.m3u8 URL from show data"""
    if "seasons" not in show_data or not show_data["seasons"]:
        return None
    
    for season in show_data["seasons"]:
        if "episodes" not in season or not season["episodes"]:
            continue
        for episode in season["episodes"]:
            if "content" in episode and "url" in episode["content"]:
                return episode["content"]["url"]
    return None

def fetch_channels():
    """Fetch channels and convert master URLs to manifest URLs"""
    
    response = requests.get(
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live",
        headers=HEADERS,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"API Error: {response.status_code}")
        return []
    
    data = response.json()
    shows_obj = data.get("shows", {})
    channels = []
    
    print(f"Processing {len(shows_obj)} shows...")
    
    for show_id, show_data in shows_obj.items():
        master_url = extract_master_url(show_data)
        if not master_url:
            continue
        
        # Convert to manifest URL
        manifest_url = master_to_manifest(master_url)
        if not manifest_url:
            continue
        
        channel_info = {
            "id": show_data.get("id", show_id),
            "name": show_data.get("title", ""),
            "logo": show_data.get("img_logo", ""),
            "stream_url": manifest_url,
            "category": show_data.get("categories", ""),
            "genre": show_data.get("genre", ""),
            "language": show_data.get("language", "")
        }
        channels.append(channel_info)
    
    print(f"Generated {len(channels)} manifest URLs")
    return channels

def generate_m3u(channels, filename="distrotv.m3u"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total Channels: {len(channels)}\n\n")
        
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["category"]}",{ch["name"]}\n')
            f.write(f"{ch['stream_url']}\n")
    
    print(f"M3U saved with {len(channels)} channels")

def main():
    print(f"Starting at {datetime.now()}")
    channels = fetch_channels()
    
    if channels:
        generate_m3u(channels)
        with open("distrotv.json", "w") as f:
            json.dump({"time": datetime.now().isoformat(), "total": len(channels), "channels": channels}, f, indent=2)
    else:
        print("No channels found")

if __name__ == "__main__":
    main()
