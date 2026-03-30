#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - Fully Dynamic with Cookie Capture
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
        self.page = None
        self.context = None

    async def scrape(self):
        """Main scraping function"""
        async with async_playwright() as p:
            # Launch browser (headless=False for debugging)
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
            )
            self.page = await self.context.new_page()

            # Go to the live TV page
            print("🌐 Navigating to toffeelive.com...")
            await self.page.goto('https://toffeelive.com/en/live', wait_until='networkidle')
            await asyncio.sleep(5)  # Wait for dynamic content

            # Extract channel list from the page
            print("📺 Extracting channel list...")
            channels_data = await self.get_channels_from_page()
            print(f"   Found {len(channels_data)} channels")

            # For each channel, capture fresh cookies and construct URL
            print("🍪 Capturing fresh cookies and constructing URLs...")
            for idx, channel in enumerate(channels_data):
                print(f"   [{idx+1}/{len(channels_data)}] Processing: {channel['name']}")
                
                # Get fresh cookies for this session
                cookies = await self.context.cookies()
                cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
                
                # Construct the correct stream URL pattern (based on your working example)
                # Convert channel name to URL-friendly format (e.g., "Ekattor TV" -> "ekattor_tv")
                url_slug = channel['name'].lower().replace(' ', '_')
                stream_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"
                
                channel['stream_url'] = stream_url
                channel['cookie'] = cookie_string
                channel['user_agent'] = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
                
                self.channels.append(channel)
                
                # Small delay to be gentle
                await asyncio.sleep(0.5)

            await self.browser.close()
            print(f"✅ Successfully processed {len(self.channels)} channels")

    async def get_channels_from_page(self) -> List[Dict]:
        """Extract channel ID, name, and logo from the page"""
        channels = []
        
        # Find all channel links
        links = await self.page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                # Extract channel ID from URL
                channel_id = href.split('/watch/')[-1].split('?')[0]
                
                # Get logo and name from image
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or 'Unknown'
                    logo = await img.get_attribute('src') or ''
                else:
                    name = 'Unknown'
                    logo = ''
                
                # Avoid duplicates
                if not any(c['id'] == channel_id for c in channels):
                    channels.append({
                        'id': channel_id,
                        'name': name,
                        'logo': logo,
                    })
        
        return channels

    def generate_m3u8(self) -> str:
        """Generate M3U8 content with cookies and headers"""
        lines = ['#EXTM3U']
        
        for channel in self.channels:
            # Determine group title based on channel name
            group_title = "Live TV"
            if any(word in channel['name'].lower() for word in ['sports', 'cricket', 'football', 'epl']):
                group_title = "Sports"
            elif any(word in channel['name'].lower() for word in ['news', 'somoy', 'jamuna', 'ekattor']):
                group_title = "News"
            elif any(word in channel['name'].lower() for word in ['movie', 'cinema', 'film', 'max', 'pix']):
                group_title = "Movies"
            elif any(word in channel['name'].lower() for word in ['kids', 'cartoon', 'pogo']):
                group_title = "Kids"
            else:
                group_title = "Entertainment"
            
            # EXTINF line
            extinf = f'#EXTINF:-1 group-title="{group_title}" tvg-id="{channel["id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}", {channel["name"]}'
            lines.append(extinf)
            
            # User-Agent header
            lines.append(f'#EXTVLCOPT:http-user-agent={channel["user_agent"]}')
            
            # Cookie header (if available)
            if channel.get('cookie'):
                lines.append(f'#EXTHTTP:{{"cookie":"{channel["cookie"]}"}}')
            
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
        
        # Save JSON
        json_output = {
            "generated_at": datetime.now().isoformat(),
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
