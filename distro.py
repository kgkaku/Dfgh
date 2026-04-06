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
    
    endpoints = [
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live",
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live&_=" + str(int(time.time()))
    ]
    
    for endpoint in endpoints:
        try:
            headers = HEADERS_TEMPLATE.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            
            print(f"Trying endpoint: {endpoint}")
            
            response = requests.get(
                endpoint, 
                headers=headers, 
                timeout=30,
                allow_redirects=True
            )
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON parsed successfully. Keys: {list(data.keys())}")
                    
                    # Handle different data structures
                    channels = []
                    
                    # Check if 'shows' key exists (from your log)
                    if "shows" in data and isinstance(data["shows"], list):
                        channels = data["shows"]
                        print(f"Found {len(channels)} channels in 'shows'")
                    
                    # Check other possible keys
                    elif "live" in data and isinstance(data["live"], list):
                        channels = data["live"]
                        print(f"Found {len(channels)} channels in 'live'")
                    
                    elif "channels" in data and isinstance(data["channels"], list):
                        channels = data["channels"]
                        print(f"Found {len(channels)} channels in 'channels'")
                    
                    elif "data" in data and isinstance(data["data"], list):
                        channels = data["data"]
                        print(f"Found {len(channels)} channels in 'data'")
                    
                    elif isinstance(data, list):
                        channels = data
                        print(f"Found {len(channels)} channels in root array")
                    
                    if channels and len(channels) > 0:
                        print(f"Sample channel keys: {list(channels[0].keys()) if channels else []}")
                        return channels
                    else:
                        print("No channels found in response")
                        print(f"Response structure: {json.dumps(data, indent=2)[:500]}")
                        
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"Response text (first 500 chars): {response.text[:500]}")
            else:
                print(f"HTTP {response.status_code}: {response.reason}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            continue
    
    return []

def extract_channel_info(channel):
    """Extract channel information from various possible field names"""
    info = {
        "id": "",
        "name": "",
        "logo": "",
        "stream_url": "",
        "token": "",
        "category": "",
        "genre": ""
    }
    
    # Try different possible field names for ID
    for key in ["id", "channel_id", "show_id", "sid"]:
        if key in channel and channel[key]:
            info["id"] = str(channel[key])
            break
    
    # Try different possible field names for Name
    for key in ["name", "title", "channel_name", "show_name", "display_name"]:
        if key in channel and channel[key]:
            info["name"] = channel[key]
            break
    
    # Try different possible field names for Logo
    for key in ["logo", "image", "thumbnail", "poster", "thumb"]:
        if key in channel and channel[key]:
            info["logo"] = channel[key]
            break
    
    # Try different possible field names for Stream URL
    for key in ["stream_url", "url", "hls_url", "playlist_url", "m3u8"]:
        if key in channel and channel[key]:
            info["stream_url"] = channel[key]
            break
    
    # Try different possible field names for Token
    for key in ["token", "access_token", "api_token", "auth_token"]:
        if key in channel and channel[key]:
            info["token"] = channel[key]
            break
    
    # Try different possible field names for Category
    for key in ["category", "group", "genre_group", "section"]:
        if key in channel and channel[key]:
            info["category"] = channel[key]
            break
    
    # Try different possible field names for Genre
    for key in ["genre", "categories", "tags", "type"]:
        if key in channel and channel[key]:
            info["genre"] = channel[key]
            break
    
    return info

def generate_m3u(channels, filename="distrotv.m3u"):
    """Generate M3U file with channel information"""
    with open(filename, "w", encoding="utf-8") as f:
        # Header with credits
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total Channels: {len(channels)}\n\n")
        
        # Write each channel
        valid_channels = 0
        for idx, channel in enumerate(channels, 1):
            info = extract_channel_info(channel)
            
            if info["stream_url"]:
                valid_channels += 1
                f.write(f'#EXTINF:-1 tvg-id="{info["id"]}" tvg-name="{info["name"]}" tvg-logo="{info["logo"]}" '
                       f'group-title="{info["category"]}" tvg-token="{info["token"]}" tvg-genre="{info["genre"]}",{info["name"]}\n')
                f.write(f"{info['stream_url']}\n")
            else:
                print(f"Warning: Channel {idx} ({info['name']}) has no stream URL")
        
        # Update total channels count in header
        if valid_channels != len(channels):
            print(f"Only {valid_channels} out of {len(channels)} channels have valid stream URLs")
    
    print(f"M3U saved to {filename} with {valid_channels} channels")

def generate_json(channels, filename="distrotv.json"):
    """Generate JSON file with complete channel data"""
    # Extract clean info for all channels
    clean_channels = []
    for channel in channels:
        clean_channels.append(extract_channel_info(channel))
    
    output_data = {
        "generated_by": "@kgkaku",
        "time": datetime.now().isoformat(),
        "total_channels": len(clean_channels),
        "channels": clean_channels,
        "raw_data_sample": channels[0] if channels else None  # Include raw data for debugging
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"JSON saved to {filename}")

def save_debug_info(data):
    """Save debug information for troubleshooting"""
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "data_type": str(type(data)),
        "data_length": len(data) if hasattr(data, '__len__') else 0,
        "sample_data": data[0] if data and len(data) > 0 else None,
        "sample_data_keys": list(data[0].keys()) if data and len(data) > 0 and isinstance(data[0], dict) else []
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
    
    # Save debug info (safe handling)
    try:
        save_debug_info(channels)
    except Exception as e:
        print(f"Could not save debug info: {e}")
    
    # Generate output files
    generate_m3u(channels)
    generate_json(channels)
    
    print(f"Channel refresh completed successfully.")

if __name__ == "__main__":
    main()
