import json
import requests
from datetime import datetime
import time
import random

# Multiple user-agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADERS_TEMPLATE = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.distro.tv/",
    "Origin": "https://www.distro.tv",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"
}

def fetch_channels():
    """Fetch live channels from DistroTV API with browser-like headers"""
    
    # Try multiple endpoints
    endpoints = [
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live",
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live&_=" + str(int(time.time())),
        "https://www.distro.tv/api/live"
    ]
    
    for endpoint in endpoints:
        try:
            # Rotate user-agent
            headers = HEADERS_TEMPLATE.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            
            print(f"Trying endpoint: {endpoint}")
            print(f"Using User-Agent: {headers['User-Agent'][:50]}...")
            
            response = requests.get(
                endpoint, 
                headers=headers, 
                timeout=30,
                allow_redirects=True
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # Try to parse JSON
                try:
                    data = response.json()
                    print(f"JSON parsed successfully. Keys: {list(data.keys())}")
                    
                    # Check different possible data structures
                    if "live" in data:
                        channels = data.get("live", [])
                    elif "channels" in data:
                        channels = data.get("channels", [])
                    elif "data" in data:
                        channels = data.get("data", [])
                    else:
                        channels = data
                    
                    if channels and len(channels) > 0:
                        print(f"Found {len(channels)} channels")
                        return channels
                    else:
                        print("No channels in response")
                        
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"Response text (first 500 chars): {response.text[:500]}")
            else:
                print(f"HTTP {response.status_code}: {response.reason}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            continue
    
    # If all endpoints fail, try to parse from HTML as fallback
    print("Trying fallback: scraping from HTML...")
    return fetch_from_html_fallback()

def fetch_from_html_fallback():
    """Fallback: Try to extract channel data from HTML response"""
    try:
        headers = HEADERS_TEMPLATE.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        
        response = requests.get("https://www.distro.tv/live/", headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Look for JavaScript variables containing channel data
            import re
            html = response.text
            
            # Try to find channel data in script tags
            patterns = [
                r'var\s+channels\s*=\s*(\[.*?\]);',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'liveChannels\s*:\s*(\[.*?\])'
            ]
            
            for pattern in patterns:
                matches = re.search(pattern, html, re.DOTALL)
                if matches:
                    try:
                        data = json.loads(matches.group(1))
                        print(f"Found channel data in HTML via pattern: {pattern}")
                        return data if isinstance(data, list) else data.get('channels', [])
                    except:
                        pass
            
            print("Could not extract channel data from HTML")
            return []
    except Exception as e:
        print(f"Fallback failed: {e}")
        return []

def generate_m3u(channels, filename="distrotv.m3u"):
    """Generate M3U file with channel information"""
    with open(filename, "w", encoding="utf-8") as f:
        # Header with credits
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total Channels: {len(channels)}\n\n")
        
        # Write each channel
        for idx, channel in enumerate(channels, 1):
            # Try different possible field names
            name = channel.get("name") or channel.get("title") or channel.get("channel_name") or f"Channel {idx}"
            logo = channel.get("logo") or channel.get("image") or channel.get("thumbnail") or ""
            url = channel.get("stream_url") or channel.get("url") or channel.get("hls_url") or ""
            token = channel.get("token") or channel.get("access_token") or ""
            category = channel.get("category") or channel.get("group") or channel.get("genre_group") or ""
            genre = channel.get("genre") or channel.get("categories") or ""
            channel_id = channel.get("id") or channel.get("channel_id") or str(idx)
            
            if url:
                # Clean up URL if needed
                if not url.startswith("http"):
                    url = "https:" + url if url.startswith("//") else url
                
                f.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{name}" tvg-logo="{logo}" '
                       f'group-title="{category}" tvg-token="{token}" tvg-genre="{genre}",{name}\n')
                f.write(f"{url}\n")
    
    print(f"M3U saved to {filename} with {len(channels)} channels")
    return len(channels)

def generate_json(channels, filename="distrotv.json"):
    """Generate JSON file with complete channel data"""
    output_data = {
        "generated_by": "@kgkaku",
        "time": datetime.now().isoformat(),
        "total_channels": len(channels),
        "channels": channels
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"JSON saved to {filename}")

def save_debug_info(channels):
    """Save debug information for troubleshooting"""
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "channel_count": len(channels),
        "sample_channel": channels[0] if channels else None,
        "all_keys": list(channels[0].keys()) if channels else []
    }
    
    with open("debug_info.json", "w", encoding="utf-8") as f:
        json.dump(debug_info, f, indent=2)
    
    print(f"Debug info saved to debug_info.json")

def main():
    print(f"Starting channel refresh at {datetime.now()}")
    print(f"Python version: {__import__('sys').version}")
    
    # Fetch channels
    channels = fetch_channels()
    
    if not channels:
        print("No channels found. Creating empty files as fallback.")
        channels = []
        # Create empty files with just headers
        with open("distrotv.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write("# by @kgkaku\n")
            f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# total Channels: 0\n")
            f.write("# ERROR: Could not fetch channels from API\n")
        
        with open("distrotv.json", "w", encoding="utf-8") as f:
            json.dump({
                "generated_by": "@kgkaku",
                "time": datetime.now().isoformat(),
                "total_channels": 0,
                "error": "Could not fetch channels from API",
                "channels": []
            }, f, indent=2)
        
        print("Created empty files due to fetch failure")
        return
    
    print(f"Found {len(channels)} channels")
    
    # Save debug info
    save_debug_info(channels)
    
    # Generate output files
    m3u_count = generate_m3u(channels)
    generate_json(channels)
    
    print(f"Channel refresh completed successfully. Processed {m3u_count} channels.")

if __name__ == "__main__":
    main()
