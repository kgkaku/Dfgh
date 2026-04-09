import json
import requests
from datetime import datetime
import time
import random
import re
import uuid

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
    Correctly convert master.m3u8 URL to working manifest URL
    Example Input: https://d35j504z0x2vu2.cloudfront.net/v1/master/0bc8e8376bd8417a1b6761138aa41c26c7309312/bollywood-masala/index.m3u8?ads.rnd=...
    Example Output: https://d35j504z0x2vu2.cloudfront.net/v1/manifest/0bc8e8376bd8417a1b6761138aa41c26c7309312/bollywood-masala/{uuid}/0.m3u8
    """
    if not master_url or "/master/" not in master_url:
        return None
    
    # Remove query parameters
    base_url = master_url.split("?")[0]
    
    # Extract the path after /master/ and before the last .m3u8
    # Expected format: /v1/master/HASH/channel-name/index.m3u8
    match = re.search(r'/master/(.+?)/([^/]+)\.m3u8$', base_url)
    if not match:
        return None
    
    channel_path = match.group(1)  # This is the HASH/channel-name
    manifest_id = str(uuid.uuid4())
    
    # Construct the correct manifest URL
    # Replace /master/ with /manifest/ and add /{uuid}/0.m3u8 at the end
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
            print(f"Failed to convert: {master_url}")
            continue
        
        # Optional: Verify URL format (for debugging)
        if manifest_url.count("/manifest/") != 1 or manifest_url.endswith(".m3u8"):
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
            # Escape special characters in name
            name = ch["name"].replace(",", "").replace("#", "")
            f.write(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name}" tvg-logo="{ch["logo"]}" group-title="{ch["category"]}",{name}\n')
            f.write(f"{ch['stream_url']}\n")
    
    print(f"M3U saved with {len(channels)} channels")

def main():
    print(f"Starting at {datetime.now()}")
    channels = fetch_channels()
    
    if channels:
        generate_m3u(channels)
        with open("distrotv.json", "w", encoding="utf-8") as f:
            json.dump({
                "time": datetime.now().isoformat(),
                "total": len(channels),
                "channels": channels
            }, f, indent=2)
        print("Files generated successfully!")
    else:
        print("No channels found. Check API response.")

if __name__ == "__main__":
    main()
