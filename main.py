#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - Optimized for GitHub Actions (headless mode)
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []
        self.edge_cache_cookie = ""

    async def scrape(self):
        async with async_playwright() as p:
            # GitHub Actions-এ headless=True হতে হবে
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']  # GitHub Actions-এর জন্য প্রয়োজন
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            # Step 1: Go to live TV page and scroll to load ALL channels
            print("🌐 Navigating to toffeelive.com...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Scroll to load all channels (lazy loading)
            print("📜 Scrolling to load all channels...")
            await self.scroll_to_load_all_channels(page)
            
            # Wait for all content to load
            await page.wait_for_timeout(3000)
            
            # Extract ALL channels
            channels_data = await self.get_all_channels_from_page(page)
            print(f"📺 Found {len(channels_data)} channels")
            
            # Remove duplicates
            unique_channels = {}
            for ch in channels_data:
                if ch['id'] not in unique_channels:
                    unique_channels[ch['id']] = ch
            
            channels_data = list(unique_channels.values())
            print(f"   After deduplication: {len(channels_data)} unique channels")

            # Step 2: Get valid Edge-Cache-Cookie from first channel
            print("\n🍪 Capturing Edge-Cache-Cookie...")
            valid_cookie = await self.get_valid_cookie_from_channel(page, channels_data[0] if channels_data else None)
            
            if not valid_cookie:
                print("⚠️ Could not capture Edge-Cache-Cookie, trying alternative method...")
                valid_cookie = await self.capture_cookie_from_network(page)
            
            # Step 3: Process all channels
            for idx, channel in enumerate(channels_data):
                print(f"   [{idx+1}/{len(channels_data)}] Processing: {channel['name']}")
                
                # Construct stream URL
                url_slug = self.get_url_slug(channel['name'], channel.get('id', ''))
                stream_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"
                
                self.channels.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'logo': channel['logo'],
                    'stream_url': stream_url,
                    'cookie': valid_cookie,
                    'group_title': self.detect_group_title(channel['name'])
                })

            await browser.close()
            print(f"\n✅ Processed {len(self.channels)} channels")

    async def scroll_to_load_all_channels(self, page):
        """Scroll the page multiple times to load all lazy-loaded channels"""
        previous_height = 0
        max_scrolls = 15
        
        for _ in range(max_scrolls):
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            
            # Check if new content loaded
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == previous_height:
                break
            previous_height = new_height
            print(f"      Scrolled, height: {new_height}px")

    async def get_all_channels_from_page(self, page) -> List[Dict]:
        """Extract ALL channels from the page"""
        channels = []
        
        # Try multiple selectors to find channel links
        links = await page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                channel_id = href.split('/watch/')[-1].split('?')[0]
                
                # Get logo and name
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or 'Unknown'
                    logo = await img.get_attribute('src') or ''
                    # Clean logo URL
                    if logo:
                        logo = logo.replace('w_480', 'f_png,w_300,q_85')
                        logo = re.sub(r',q_\d+', '', logo)
                else:
                    name = 'Unknown'
                    logo = ''
                
                channels.append({
                    'id': channel_id,
                    'name': name.strip(),
                    'logo': logo,
                })
        
        return channels

    async def get_valid_cookie_from_channel(self, page, channel) -> str:
        """Load a channel to capture valid Edge-Cache-Cookie"""
        if not channel:
            return ""
        
        print(f"   📡 Loading {channel['name']} to capture cookie...")
        
        watch_url = f"https://toffeelive.com/en/watch/{channel['id']}"
        try:
            await page.goto(watch_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(8000)  # Wait for video player
            
            # Capture cookies
            cookies = await page.context.cookies()
            edge_cache = next((c for c in cookies if c['name'] == 'Edge-Cache-Cookie'), None)
            
            if edge_cache:
                cookie_value = f"Edge-Cache-Cookie={edge_cache['value']}"
                print(f"      ✅ Edge-Cache-Cookie captured")
                return cookie_value
        except Exception as e:
            print(f"      ⚠️ Error loading channel: {e}")
        
        return ""

    async def capture_cookie_from_network(self, page) -> str:
        """Alternative: capture cookie from network responses"""
        edge_cookie = ""
        
        def on_response(response):
            nonlocal edge_cookie
            headers = response.headers
            set_cookie = headers.get('set-cookie', '')
            if 'Edge-Cache-Cookie' in set_cookie:
                match = re.search(r'Edge-Cache-Cookie=([^;]+)', set_cookie)
                if match:
                    edge_cookie = f"Edge-Cache-Cookie={match.group(1)}"
        
        page.on('response', on_response)
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        return edge_cookie

    def get_url_slug(self, name: str, channel_id: str) -> str:
        """Convert channel name to URL-friendly format"""
        special_mappings = {
            'Ekattor TV': 'ekattor_tv',
            'Somoy TV': 'somoy_tv',
            'Jamuna TV': 'jamuna_tv',
            'Channel i': 'channel_i',
            'Independent TV': 'independent_tv',
            'Asian TV': 'asian_tv',
            'Bangla TV': 'bangla_tv',
            'Global TV': 'global_tv',
            'Channel S': 'channel_s',
            'Ananda TV': 'ananda_tv',
            'Bijoy TV': 'bijoy_tv',
            'Mohona TV': 'mohona_tv',
            'Desh TV': 'desh_tv',
            'Nexus TV': 'nexus_tv',
            'Movie Bangla': 'movie_bangla',
            'Ekhon TV': 'ekhon_tv',
            'Sony Ten Sports 1 HD': 'sony_ten_sports_1_hd',
            'Sony Ten Sports 2 HD': 'sony_ten_sports_2_hd',
            'EPL channel 1': 'epl_channel_1',
            'EPL channel 2': 'epl_channel_2',
            'EPL channel 3': 'epl_channel_3',
            'EPL Channel 4': 'epl_channel_4',
            'EPL Channel 5': 'epl_channel_5',
            'EPL Channel 6': 'epl_channel_6',
            'Eurosport HD': 'eurosport_hd',
            'Sony Ten Cricket': 'sony_ten_cricket',
            'CNN': 'cnn',
            'BFL | Live 1': 'bfl_live_1',
            'BFL | Live 2': 'bfl_live_2',
            'BFL | Live 3': 'bfl_live_3',
            'BFL | Live 4': 'bfl_live_4',
            'Sony MAX HD': 'sony_max_hd',
            'Sony MAX': 'sony_max',
            'Sony MAX 2': 'sony_max_2',
            'Sony PIX HD': 'sony_pix_hd',
            'B4U Movies APAC': 'b4u_movies_apac',
            '& Pictures HD': 'and_pictures_hd',
            'Zee Bangla Cinema': 'zee_bangla_cinema',
            'Zee Cinema HD': 'zee_cinema_hd',
            'Zee Action': 'zee_action',
            'Zee Bollywood': 'zee_bollywood',
            'Zing': 'zing',
            'Zee Bangla': 'zee_bangla',
            'HUM': 'hum',
            'HUM Sitaray': 'hum_sitaray',
            'HUM Masala': 'hum_masala',
            'Sony Aath': 'sony_aath',
            'B4U Music': 'b4u_music',
            'Sony Entertainment Television': 'sony_entertainment_television',
            'Sony SAB HD': 'sony_sab_hd',
            'Zee TV HD': 'zee_tv_hd',
            '&TV HD': 'and_tv_hd',
            'TLC': 'tlc',
            'TLC HD': 'tlc_hd',
            'Animal Planet HD': 'animal_planet_hd',
            'Animal Planet': 'animal_planet',
            'Sony BBC Earth HD': 'sony_bbc_earth_hd',
            'Discovery HD': 'discovery_hd',
            'Discovery': 'discovery',
            'Discovery Science': 'discovery_science',
            'Discovery Turbo': 'discovery_turbo',
            'Investigation Discovery HD': 'investigation_discovery_hd',
            'Cartoon Network HD +': 'cartoon_network_hd',
            'Cartoon Network': 'cartoon_network',
            'POGO': 'pogo',
            'Discovery Kids': 'discovery_kids',
            'Sony YAY': 'sony_yay',
        }
        
        if name in special_mappings:
            return special_mappings[name]
        
        return name.lower().replace(' ', '_')

    def detect_group_title(self, name: str) -> str:
        name_lower = name.lower()
        if any(word in name_lower for word in ['sports', 'cricket', 'football', 'epl', 'ten', 'eurosport']):
            return "স্পোর্টস চ্যানেল"
        elif any(word in name_lower for word in ['news', 'somoy', 'jamuna', 'ekattor', 'independent', 'global', 'channel i', 'channel s', 'ananda', 'bijoy', 'mohona', 'desh', 'nexus', 'ekhon']):
            return "বাংলাদেশি চ্যানেল"
        elif any(word in name_lower for word in ['movie', 'cinema', 'film', 'max', 'pix', 'b4u', '& pictures', 'zee', 'zing']):
            return "সিনেমা চ্যানেল"
        elif any(word in name_lower for word in ['kids', 'cartoon', 'pogo', 'discovery kids', 'sony yay']):
            return "কিডস চ্যানেল"
        else:
            return "বিনোদন চ্যানেল"

    def generate_m3u8(self) -> str:
        """Generate M3U8 content matching working format"""
        lines = ['#EXTM3U']
        
        for channel in self.channels:
            extinf = f'#EXTINF:-1 group-title="{channel["group_title"]}" tvg-logo="{channel["logo"]}", {channel["name"]}'
            lines.append(extinf)
            lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            
            if channel.get('cookie'):
                cookie_json = json.dumps({"cookie": channel['cookie']})
                lines.append(f'#EXTHTTP:{cookie_json}')
            
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)

    def save_files(self):
        m3u_content = self.generate_m3u8()
        with open('toffee.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        json_output = {
            "generated_at": datetime.now().isoformat(),
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Files saved!")
        print(f"   - Total channels: {len(self.channels)}")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.save_files()

if __name__ == "__main__":
    asyncio.run(main())
