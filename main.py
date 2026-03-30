#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - Fully Dynamic with Live Cookie Capture
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []
        self.cookie_string = ""
        self.user_agent = ""

    async def scrape(self):
        """Main scraping function"""
        async with async_playwright() as p:
            # Launch browser (headless=True for GitHub Actions)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
            )
            page = await context.new_page()

            # Go to the live TV page
            print("🌐 Navigating to toffeelive.com...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle')
            await page.wait_for_timeout(5000)  # Wait for dynamic content

            # 1. Extract channel list
            print("📺 Extracting channel list...")
            channels_data = await self.get_channels_from_page(page)
            print(f"   Found {len(channels_data)} channels")

            # 2. Get fresh cookies and user-agent
            cookies = await context.cookies()
            self.cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
            self.user_agent = await page.evaluate('navigator.userAgent')
            print(f"🍪 Fresh cookies captured: {self.cookie_string[:100]}...")

            # 3. Construct channels with correct URL pattern
            for channel in channels_data:
                # Convert channel name to URL-friendly format (e.g., "Ekattor TV" -> "ekattor_tv")
                url_slug = channel['name'].lower().replace(' ', '_')
                stream_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"
                
                self.channels.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'logo': channel['logo'],
                    'stream_url': stream_url,
                    'group_title': self.detect_group_title(channel['name'])
                })

            await browser.close()
            print(f"✅ Successfully processed {len(self.channels)} channels")

    async def get_channels_from_page(self, page) -> List[Dict]:
        """Extract channel ID, name, and logo from the page"""
        channels = []
        
        # Find all channel links
        links = await page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                channel_id = href.split('/watch/')[-1].split('?')[0]
                
                # Get logo and name from image
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or 'Unknown'
                    logo = await img.get_attribute('src') or ''
                    # Clean logo URL if needed
                    if logo and 'w_480' in logo:
                        logo = logo.replace('w_480', 'f_png,w_300,q_85')
                else:
                    name = 'Unknown'
                    logo = ''
                
                if not any(c['id'] == channel_id for c in channels):
                    channels.append({
                        'id': channel_id,
                        'name': name.strip(),
                        'logo': logo,
                    })
        
        return channels

    def detect_group_title(self, name: str) -> str:
        """Detect group title based on channel name"""
        name_lower = name.lower()
        if any(word in name_lower for word in ['sports', 'cricket', 'football', 'epl', 'ten']):
            return "স্পোর্টস চ্যানেল"
        elif any(word in name_lower for word in ['news', 'somoy', 'jamuna', 'ekattor', 'independent', 'global', 'channel']):
            return "বাংলাদেশি চ্যানেল"
        elif any(word in name_lower for word in ['movie', 'cinema', 'film', 'max', 'pix', 'action', 'bollywood']):
            return "সিনেমা চ্যানেল"
        elif any(word in name_lower for word in ['kids', 'cartoon', 'pogo', 'discovery', 'animal planet']):
            return "কিডস চ্যানেল"
        else:
            return "বিনোদন চ্যানেল"

    def generate_m3u8(self) -> str:
        """Generate M3U8 content with proper headers and cookies"""
        lines = ['#EXTM3U']
        
        for channel in self.channels:
            # EXTINF line
            extinf = f'#EXTINF:-1 group-title="{channel["group_title"]}" tvg-id="{channel["id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}", {channel["name"]}'
            lines.append(extinf)
            
            # User-Agent header
            lines.append(f'#EXTVLCOPT:http-user-agent={self.user_agent}')
            
            # Cookie header (only if cookie string is not empty)
            if self.cookie_string:
                cookie_json = json.dumps({"cookie": self.cookie_string})
                lines.append(f'#EXTHTTP:{cookie_json}')
            
            # Stream URL
            lines.append(channel['stream_url'])
            lines.append('')  # Empty line for readability
        
        return '\n'.join(lines)

    def save_files(self):
        """Save both M3U and JSON files"""
        # Save M3U8
        m3u_content = self.generate_m3u8()
        with open('toffee.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        # Save JSON (for debugging or alternative use)
        json_output = {
            "generated_at": datetime.now().isoformat(),
            "user_agent": self.user_agent,
            "cookie": self.cookie_string,
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Files saved successfully!")
        print(f"   - toffee.m3u: {len(m3u_content)} bytes")
        print(f"   - toffee.json: {len(json.dumps(json_output))} bytes")
        print(f"   - Total channels: {len(self.channels)}")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.save_files()

if __name__ == "__main__":
    asyncio.run(main())
