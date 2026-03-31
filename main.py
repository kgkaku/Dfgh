#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - COMPLETE SOLUTION
Captures ALL channels with correct logos and working streams
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
        self.all_cookies = {}
        self.logs = []

    def log(self, message: str, level: str = "INFO"):
        """Print log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        self.logs.append(f"[{timestamp}] {message}")

    async def scrape(self):
        start_time = datetime.now()
        self.log("🚀 Starting Toffee Scraper...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            # Step 1: Load live TV page
            self.log("🌐 Navigating to toffeelive.com/en/live...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Step 2: Scroll to load ALL channels
            self.log("📜 Scrolling to load all channels...")
            total_loaded = await self.smart_scroll(page)
            self.log(f"   ✓ Loaded {total_loaded} channel cards")
            
            # Step 3: Extract ALL channel information
            self.log("📺 Extracting channel data from page...")
            channels_data = await self.get_all_channels_with_details(page)
            self.log(f"   ✓ Found {len(channels_data)} raw channels")
            
            # Step 4: Remove duplicates
            unique_channels = {}
            for ch in channels_data:
                if ch['id'] not in unique_channels:
                    unique_channels[ch['id']] = ch
            
            channels_data = list(unique_channels.values())
            self.log(f"   ✓ After deduplication: {len(channels_data)} unique channels")
            
            # Step 5: Get fresh cookie from first channel
            self.log("🍪 Capturing Edge-Cache-Cookie...")
            valid_cookie = await self.get_cookie_with_retry(page, channels_data[0] if channels_data else None)
            
            if not valid_cookie:
                self.log("⚠️ WARNING: Could not capture Edge-Cache-Cookie", "WARN")
                self.log("   Trying alternative method...")
                valid_cookie = await self.capture_cookie_from_network(page)
            
            # Step 6: Process all channels with detailed logging
            self.log(f"\n📡 Processing {len(channels_data)} channels...")
            self.log("=" * 50)
            
            success_count = 0
            fail_count = 0
            
            for idx, channel in enumerate(channels_data):
                try:
                    # Show progress
                    progress = f"[{idx+1}/{len(channels_data)}]"
                    
                    # Construct URL
                    url_slug = self.slugify(channel['name'])
                    stream_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"
                    
                    # Validate logo
                    logo = channel['logo']
                    if not logo or logo == '':
                        logo = "https://www.solidbackgrounds.com/images/1920x1080/1920x1080-bright-green-solid-color-background.jpg"
                        self.log(f"   {progress} {channel['name']} - ⚠️ No logo, using default", "WARN")
                    else:
                        self.log(f"   {progress} {channel['name']} - ✓ Logo OK", "INFO")
                    
                    self.channels.append({
                        'id': channel['id'],
                        'name': channel['name'],
                        'logo': logo,
                        'stream_url': stream_url,
                        'cookie': valid_cookie
                    })
                    success_count += 1
                    
                except Exception as e:
                    self.log(f"   [{idx+1}/{len(channels_data)}] {channel['name']} - ❌ Error: {str(e)[:50]}", "ERROR")
                    fail_count += 1
                
                # Show progress every 10 channels
                if (idx + 1) % 10 == 0:
                    self.log(f"   📊 Progress: {idx+1}/{len(channels_data)} channels processed")
            
            await browser.close()
            
            # Summary
            elapsed = (datetime.now() - start_time).total_seconds()
            self.log("=" * 50)
            self.log(f"✅ Scraping completed in {elapsed:.1f} seconds")
            self.log(f"   ✓ Success: {success_count} channels")
            self.log(f"   ✗ Failed: {fail_count} channels")
            self.log(f"   📺 Total: {len(self.channels)} channels")

    async def smart_scroll(self, page) -> int:
        """Smart scroll that stops when no new channels load"""
        last_count = 0
        same_count = 0
        
        for scroll_num in range(1, 21):
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            
            # Count current channels
            current_count = await page.evaluate('document.querySelectorAll(\'a[href*="/watch/"]\').length')
            
            self.log(f"   Scroll {scroll_num}: {current_count} channels loaded")
            
            if current_count == last_count:
                same_count += 1
                if same_count >= 3:
                    self.log(f"   ✓ No new channels after {scroll_num} scrolls")
                    break
            else:
                same_count = 0
                last_count = current_count
            
            # Stop if we have enough
            if current_count >= 80:
                self.log(f"   ✓ Target reached: {current_count} channels")
                break
        
        return current_count

    async def get_all_channels_with_details(self, page) -> List[Dict]:
        """Extract ALL channels with correct logos"""
        channels = []
        
        # Get all channel links
        links = await page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                channel_id = href.split('/watch/')[-1].split('?')[0]
                
                # Try multiple methods to get logo
                logo = ""
                name = ""
                
                # Method 1: Get from img tag
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or ''
                    logo = await img.get_attribute('src') or ''
                
                # Method 2: If no name, try text
                if not name:
                    text_elem = await link.query_selector('p, span, .title')
                    if text_elem:
                        name = await text_elem.inner_text()
                
                # Method 3: If still no name, use ID
                if not name:
                    name = channel_id
                
                # Clean logo URL
                if logo:
                    # Get high quality logo
                    logo = re.sub(r'/w_\d+,q_\d+,f_\w+/', '/f_png,w_300,q_85/', logo)
                    logo = re.sub(r',q_\d+', '', logo)
                    
                    # Ensure it starts with https
                    if not logo.startswith('http'):
                        logo = f"https://assets-prod.services.toffeelive.com{logo}"
                
                channels.append({
                    'id': channel_id,
                    'name': name.strip(),
                    'logo': logo,
                })
        
        return channels

    async def get_cookie_with_retry(self, page, channel) -> str:
        """Get cookie with retry logic"""
        if not channel:
            return ""
        
        self.log(f"   📡 Loading {channel['name']} for cookie...")
        
        for attempt in range(1, 4):
            try:
                watch_url = f"https://toffeelive.com/en/watch/{channel['id']}"
                await page.goto(watch_url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(5000)
                
                # Check for video element
                video_exists = await page.evaluate('!!document.querySelector("video")')
                if video_exists:
                    self.log(f"   ✓ Video player loaded on attempt {attempt}")
                
                # Get cookies
                cookies = await page.context.cookies()
                
                # Look for Edge-Cache-Cookie
                edge_cache = next((c for c in cookies if c['name'] == 'Edge-Cache-Cookie'), None)
                if edge_cache:
                    cookie_value = f"Edge-Cache-Cookie={edge_cache['value']}"
                    self.log(f"   ✅ Edge-Cache-Cookie captured (expires: {edge_cache.get('expires', 'unknown')})")
                    return cookie_value
                
                # Look for any useful cookie
                if cookies:
                    self.log(f"   ⚠️ Found {len(cookies)} cookies but no Edge-Cache-Cookie")
                
            except Exception as e:
                self.log(f"   ⚠️ Attempt {attempt} failed: {str(e)[:50]}")
                if attempt < 3:
                    await page.wait_for_timeout(2000)
        
        return ""

    async def capture_cookie_from_network(self, page) -> str:
        """Fallback: capture cookie from network response"""
        edge_cookie = ""
        
        def on_response(response):
            nonlocal edge_cookie
            headers = response.headers
            set_cookie = headers.get('set-cookie', '')
            if 'Edge-Cache-Cookie' in set_cookie:
                match = re.search(r'Edge-Cache-Cookie=([^;]+)', set_cookie)
                if match:
                    edge_cookie = f"Edge-Cache-Cookie={match.group(1)}"
                    self.log(f"   📡 Captured from network response")
        
        page.on('response', on_response)
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(3000)
        
        return edge_cookie

    def slugify(self, name: str) -> str:
        """Convert channel name to URL slug"""
        # Common special cases
        special = {
            '& Pictures HD': 'and_pictures_hd',
            '&TV HD': 'and_tv_hd',
            'BFL | Live 1': 'bfl_live_1',
            'BFL | Live 2': 'bfl_live_2',
            'BFL | Live 3': 'bfl_live_3',
            'BFL | Live 4': 'bfl_live_4',
            'EPL channel 1': 'epl_channel_1',
            'EPL channel 2': 'epl_channel_2',
            'EPL channel 3': 'epl_channel_3',
            'EPL Channel 4': 'epl_channel_4',
            'EPL Channel 5': 'epl_channel_5',
            'EPL Channel 6': 'epl_channel_6',
            'Sony Ten Sports 1 HD': 'sony_ten_sports_1_hd',
            'Sony Ten Sports 2 HD': 'sony_ten_sports_2_hd',
            'Sony Ten Cricket': 'sony_ten_cricket',
            'Eurosport HD': 'eurosport_hd',
            'Cartoon Network HD +': 'cartoon_network_hd',
            'Investigation Discovery HD': 'investigation_discovery_hd',
            'Sony BBC Earth HD': 'sony_bbc_earth_hd',
            'Animal Planet HD': 'animal_planet_hd',
        }
        
        if name in special:
            return special[name]
        
        # Generic conversion
        slug = name.lower()
        slug = slug.replace(' ', '_')
        slug = slug.replace('|', '')
        slug = slug.replace('&', 'and')
        slug = slug.replace('+', 'plus')
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        return slug

    def generate_ott_navigator_m3u(self) -> str:
        """Generate toffee-ott-navigator.m3u"""
        now = datetime.now()
        lines = [
            '#EXTM3U',
            f'# By @kgkaku',
            f'# Scrapped on {now.strftime("%Y_%m_%d")} {now.strftime("%H:%M:%S")}',
            f'# Total channels: {len(self.channels)}',
            '',
            '#EXTINF:-1 tvg-name="kgkaku" tvg-logo="https://www.solidbackgrounds.com/images/1920x1080/1920x1080-bright-green-solid-color-background.jpg",Welcome',
            'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
            ''
        ]
        
        for channel in self.channels:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}", {channel["name"]}')
            lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            if channel.get('cookie'):
                cookie_json = json.dumps({"cookie": channel['cookie']})
                lines.append(f'#EXTHTTP:{cookie_json}')
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)

    def generate_nsplayer_m3u(self) -> str:
        """Generate toffee-nsplayer.m3u"""
        now = datetime.now()
        lines = [
            '#EXTM3U',
            f'# By @kgkaku',
            f'# Scrapped on {now.strftime("%Y_%m_%d")} {now.strftime("%H:%M:%S")}',
            f'# Total channels: {len(self.channels)}',
            ''
        ]
        
        for channel in self.channels:
            channel_info = {
                "name": channel['name'],
                "link": channel['stream_url'],
                "logo": channel['logo'],
                "cookie": channel.get('cookie', '')
            }
            lines.append(f'#EXTINF:-1,{json.dumps(channel_info, ensure_ascii=False)}')
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)

    def save_files(self):
        """Save all files"""
        self.log("\n💾 Saving files...")
        
        ott_content = self.generate_ott_navigator_m3u()
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write(ott_content)
        self.log(f"   ✓ toffee-ott-navigator.m3u ({len(ott_content)} bytes)")
        
        ns_content = self.generate_nsplayer_m3u()
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            f.write(ns_content)
        self.log(f"   ✓ toffee-nsplayer.m3u ({len(ns_content)} bytes)")
        
        json_output = {
            "generated_at": datetime.now().isoformat(),
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        self.log(f"   ✓ toffee.json ({len(json.dumps(json_output))} bytes)")
        
        self.log(f"\n✅ Total channels saved: {len(self.channels)}")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.save_files()

if __name__ == "__main__":
    asyncio.run(main())
