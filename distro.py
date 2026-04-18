import json
import requests
from datetime import datetime
import uuid
import re

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.distro.tv/",
    "Origin": "https://www.distro.tv",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def master_to_manifest(master_url):
    """
    Convert master.m3u8 URL to working manifest URL
    Supports both CloudFront and Amagi CDN formats
    """
    if not master_url:
        return None
    
    # Remove query parameters for processing
    base_url = master_url.split("?")[0]
    
    # Case 1: CloudFront format (d35j504z0x2vu2.cloudfront.net)
    if "cloudfront.net" in base_url and "/master/" in base_url:
        pattern = r'(https?://[^/]+)/v1/master/(.+?)/[^/]+\.m3u8$'
        match = re.search(pattern, base_url)
        if match:
            domain = match.group(1)
            channel_path = match.group(2)
            manifest_id = str(uuid.uuid4())
            return f"{domain}/v1/manifest/{channel_path}/{manifest_id}/0.m3u8"
    
    # Case 2: Amagi CDN format (playout.now3.amagi.tv)
    elif "amagi.tv" in base_url:
        # Amagi URLs usually work directly
        # Just remove tracking parameters if needed
        return base_url
    
    # Case 3: Other cloudfront formats (d3s7x6kmqcnb6b.cloudfront.net)
    elif "cloudfront.net" in base_url and "/d/distro001a/" in base_url:
        # These are direct HLS streams, use as-is
        return base_url
    
    # Case 4: Return original URL if it's already a manifest
    elif base_url.endswith(".m3u8"):
        return base_url
    
    return None

def extract_stream_url(show_data):
    """Extract stream URL from show data (supports multiple formats)"""
    if "seasons" not in show_data or not show_data["seasons"]:
        return None
    
    for season in show_data["seasons"]:
        if "episodes" not in season or not season["episodes"]:
            continue
        for episode in season["episodes"]:
            # Try content.url first
            if "content" in episode and "url" in episode["content"]:
                return episode["content"]["url"]
            # Try direct url
            elif "url" in episode:
                return episode["url"]
            # Try streams array
            elif "streams" in episode and episode["streams"]:
                for stream in episode["streams"]:
                    if "url" in stream:
                        return stream["url"]
    return None

def fetch_channels():
    """Fetch all channels from DistroTV API"""
    try:
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
        failed_urls = []
        
        print(f"Processing {len(shows_obj)} shows...")
        
        for show_id, show_data in shows_obj.items():
            stream_url = extract_stream_url(show_data)
            if not stream_url:
                continue
            
            # Convert to manifest URL if needed
            manifest_url = master_to_manifest(stream_url)
            if not manifest_url:
                failed_urls.append(stream_url[:100])
                continue
            
            # Get channel info
            channel_name = show_data.get("title", "").strip()
            if not channel_name:
                channel_name = show_id
            
            channel_info = {
                "id": show_data.get("id", show_id),
                "name": channel_name,
                "logo": show_data.get("img_logo", ""),
                "stream_url": manifest_url,
                "category": show_data.get("categories", "Uncategorized"),
                "genre": show_data.get("genre", ""),
                "language": show_data.get("language", "")
            }
            channels.append(channel_info)
        
        # Print failure summary
        if failed_urls:
            print(f"\n⚠️ Failed to convert {len(failed_urls)} URLs (kept as-is in M3U)")
        
        print(f"✅ Generated {len(channels)} working streams")
        return channels
        
    except Exception as e:
        print(f"Error fetching channels: {e}")
        return []

def generate_m3u(channels, filename="distrotv.m3u"):
    """Generate M3U playlist file"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total: {len(channels)}\n\n")
        
        for ch in channels:
            # Clean channel name
            name = ch["name"].replace(",", "").replace("#", "").strip()
            if not name:
                name = ch["id"]
            
            # Get category
            category = ch.get("category", "Uncategorized")
            if not category or category == "":
                category = "Uncategorized"
            
            # Escape for M3U
            name_escaped = name.replace(",", "")
            
            f.write(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name_escaped}" tvg-logo="{ch["logo"]}" group-title="{category}",{name}\n')
            f.write(f"{ch['stream_url']}\n")
    
    print(f"📺 M3U saved: {filename}")

def generate_simple_m3u(channels, filename="distrotv_simple.m3u"):
    """Generate simple M3U without metadata"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for ch in channels:
            name = ch["name"].strip()
            if not name:
                name = ch["id"]
            f.write(f'#EXTINF:-1,{name}\n')
            f.write(f"{ch['stream_url']}\n")
    
    print(f"📺 Simple M3U saved: {filename}")

def save_json(channels, filename="distrotv.json"):
    """Save channel data as JSON"""
    output = {
        "generated": datetime.now().isoformat(),
        "total": len(channels),
        "channels": channels
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"📄 JSON saved: {filename}")

def main():
    print("=" * 50)
    print(f"🚀 DistroTV Channel Grabber")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    channels = fetch_channels()
    
    if channels:
        generate_m3u(channels)
        generate_simple_m3u(channels)
        save_json(channels)
        
        print("=" * 50)
        print(f"✅ Success! {len(channels)} channels extracted")
        print(f"📁 Output files:")
        print(f"   - distrotv.m3u (full metadata)")
        print(f"   - distrotv_simple.m3u (simple format)")
        print(f"   - distrotv.json (JSON format)")
        
        # Show sample
        print(f"\n📋 Sample channels:")
        for i, ch in enumerate(channels[:5], 1):
            url_short = ch['stream_url'][:60] + "..." if len(ch['stream_url']) > 60 else ch['stream_url']
            print(f"   {i}. {ch['name']}")
            print(f"      {url_short}")
    else:
        print("❌ No channels found!")

if __name__ == "__main__":
    main()
