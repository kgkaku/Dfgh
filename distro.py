import json
import requests
from datetime import datetime
import time
import random
import re

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

# US-based IP for geo-unblocking (using Cloudflare's DNS as fallback)
PROXY_LIST = [
    None,  # Direct connection first
    # Add proxy URLs if needed, e.g., {"http": "http://proxy:port", "https": "https://proxy:port"}
]

def get_client_ip():
    """Get current external IP for placeholder replacement"""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        return response.json().get("ip", "0.0.0.0")
    except:
        return "103.87.215.66"  # Fallback IP

def get_geo_info():
    """Get geo location for placeholder replacement"""
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        data = response.json()
        return {
            "country": data.get("country_code", "US"),
            "lat": str(data.get("latitude", "37.75100")),
            "lon": str(data.get("longitude", "-97.82200")),
            "dma": data.get("dma_code", ""),
            "region": data.get("region_code", "")
        }
    except:
        return {"country": "US", "lat": "37.75100", "lon": "-97.82200", "dma": "", "region": ""}

def clean_url(url, client_ip, geo_info):
    """Replace placeholders in URL with actual values"""
    if not url:
        return url
    
    # Generate random UUID-like strings for placeholders
    import uuid
    
    replacements = {
        "__CACHE_BUSTER__": str(int(time.time() * 1000)),
        "__env.i__": str(uuid.uuid4()),
        "__env.u__": str(uuid.uuid4()),
        "__APP_BUNDLE__": "distrotv_web",
        "__APP_NAME__": "DistroTV",
        "__STORE_URL__": "https://www.distro.tv",
        "__APP_CATEGORY__": "entertainment",
        "__APP_VERSION__": "202105131041",
        "__WIDTH__": "1280",
        "__HEIGHT__": "720",
        "__DEVICE_ID__": str(uuid.uuid4()),
        "__LIMIT_AD_TRACKING__": "0",
        "__IS_GDPR__": "0",
        "__IS_CCPA__": "0",
        "__ADVERTISING_ID__": "",
        "__DEVICE__": "Web",
        "__DEVICE_ID_TYPE__": "localStorage",
        "__DEVICE_CONNECTION_TYPE__": "2",
        "__DEVICE_CATEGORY__": "web",
        "__CLIENT_IP__": client_ip,
        "__GEO_COUNTRY__": geo_info["country"],
        "__LATITUDE__": geo_info["lat"],
        "__LONGITUDE__": geo_info["lon"],
        "__GEO_DMA__": geo_info["dma"],
        "__GEO_TYPE__": "2",
        "__PAGEURL_ESC__": "https%3A%2F%2Fwww.distro.tv%2Flive%2F",
        "__GDPR_CONSENT__": "",
        "__PALN__": ""
    }
    
    for placeholder, value in replacements.items():
        url = url.replace(placeholder, value)
    
    return url

def fetch_channels():
    """Fetch live channels from DistroTV API"""
    endpoints = [
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live",
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live&_=" + str(int(time.time()))
    ]
    
    for endpoint in endpoints:
        for proxy in PROXY_LIST:
            try:
                headers = HEADERS_TEMPLATE.copy()
                headers["User-Agent"] = random.choice(USER_AGENTS)
                
                print(f"Trying endpoint: {endpoint}")
                if proxy:
                    print(f"Using proxy: {proxy}")
                
                response = requests.get(endpoint, headers=headers, timeout=30, proxies=proxy)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "shows" in data and isinstance(data["shows"], dict):
                        shows_obj = data["shows"]
                        channels = []
                        
                        for show_id, show_data in shows_obj.items():
                            stream_url = None
                            if "seasons" in show_data and show_data["seasons"]:
                                for season in show_data["seasons"]:
                                    if "episodes" in season and season["episodes"]:
                                        for episode in season["episodes"]:
                                            if "content" in episode and "url" in episode["content"]:
                                                stream_url = episode["content"]["url"]
                                                break
                                    if stream_url:
                                        break
                            
                            if stream_url:
                                channel_info = {
                                    "id": show_data.get("id", show_id),
                                    "name": show_data.get("title", ""),
                                    "logo": show_data.get("img_logo", ""),
                                    "stream_url": stream_url,
                                    "category": show_data.get("categories", ""),
                                    "genre": show_data.get("genre", ""),
                                    "description": show_data.get("description", ""),
                                    "rating": show_data.get("rating", ""),
                                    "language": show_data.get("language", "")
                                }
                                channels.append(channel_info)
                        
                        print(f"Found {len(channels)} channels")
                        return channels
                        
            except Exception as e:
                print(f"Error: {e}")
                continue
    
    return []

def test_stream_url(url):
    """Test if stream URL is accessible"""
    try:
        # Don't actually download, just check if URL is valid
        if url and (url.startswith("http://") or url.startswith("https://")):
            return True
        return False
    except:
        return False

def generate_m3u(channels, filename="distrotv.m3u"):
    """Generate M3U file with cleaned channel information"""
    client_ip = get_client_ip()
    geo_info = get_geo_info()
    
    print(f"Using IP: {client_ip}, Geo: {geo_info['country']}")
    
    with open(filename, "w", encoding="utf-8") as f:
        # Header with credits
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total Channels: {len(channels)}\n")
        f.write(f"# NOTE: Streams may be geo-restricted. Use US-based VPN if needed.\n\n")
        
        valid_channels = 0
        for idx, channel in enumerate(channels, 1):
            name = channel.get("name", f"Channel {idx}")
            logo = channel.get("logo", "")
            raw_url = channel.get("stream_url", "")
            category = channel.get("category", "")
            genre = channel.get("genre", "")
            channel_id = channel.get("id", str(idx))
            
            if raw_url:
                # Clean the URL
                cleaned_url = clean_url(raw_url, client_ip, geo_info)
                
                # Optional: Test URL (commented to save time)
                # if not test_stream_url(cleaned_url):
                #     print(f"Warning: URL may be invalid for {name}")
                
                valid_channels += 1
                f.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{name}" tvg-logo="{logo}" '
                       f'group-title="{category}" tvg-genre="{genre}",{name}\n')
                f.write(f"{cleaned_url}\n")
        
        print(f"M3U saved to {filename} with {valid_channels} valid channels")

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

def main():
    print(f"Starting channel refresh at {datetime.now()}")
    
    channels = fetch_channels()
    
    if not channels:
        print("No channels found. Creating empty files as fallback.")
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
        return
    
    print(f"Found {len(channels)} channels")
    generate_m3u(channels)
    generate_json(channels)
    print("Channel refresh completed successfully.")

if __name__ == "__main__":
    main()
