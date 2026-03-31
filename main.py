#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - FIXED VERSION
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
        self.cookie = ""

    async def scrape(self):
        start_time = datetime.now()
        print("\n" + "="*70)
        print("🚀 TOFFEE LIVE CHANNEL SCRAPER - FIXED VERSION")
        print("="*70 + "\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
            )
            page = await context.new_page()

            # STEP 1: Get ALL channel IDs from live page
            print("📺 STEP 1: Loading all channels...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Aggressive scrolling to load ALL
            print("   Scrolling to load...")
            prev_count = 0
            for i in range(20):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                current = await page.evaluate('document.querySelectorAll(\'a[href*="/watch/"]\').length')
                print(f"      Scroll {i+1}: {current} channels")
                if current == prev_count:
                    break
                prev_count = current
            
            # Get ALL links
            links = await page.query_selector_all('a[href*="/watch/"]')
            print(f"\n   ✓ Found {len(links)} links")
            
            # Extract unique channels
            channels_dict = {}
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    channel_id = href.split('/watch/')[-1].split('?')[0]
                    img = await link.query_selector('img')
                    if img:
                        name = await img.get_attribute('alt') or ''
                        logo = await img.get_attribute('src') or ''
                    else:
                        name = channel_id
                        logo = ''
                    
                    if channel_id not in channels_dict:
                        channels_dict[channel_id] = {
                            'id': channel_id,
                            'name': name.strip(),
                            'logo': logo
                        }
            
            channels_list = list(channels_dict.values())
            print(f"   ✓ Unique channels: {len(channels_list)}")
            
            # STEP 2: Get cookie by actually playing a video
            print("\n🍪 STEP 2: Getting Edge-Cache-Cookie...")
            cookie = await self.get_cookie(page, context, "PiL635oBEef-9-uV2uCe")
            
            if not cookie:
                print("   Trying alternative channel...")
                cookie = await self.get_cookie(page, context, "PS_La5oBNnOkwJLWLRN_")
            
            if cookie:
                print(f"   ✅ Cookie captured: {cookie[:80]}...")
            else:
                print("   ⚠️ No cookie found, streams may not work")
            
            # STEP 3: Get stream URLs for ALL channels
            print(f"\n🎬 STEP 3: Getting stream URLs for {len(channels_list)} channels...")
            print("   (This takes time, please wait)\n")
            
            for idx, channel in enumerate(channels_list):
                # Show progress
                if (idx + 1) % 10 == 0:
                    print(f"   Progress: {idx+1}/{len(channels_list)} channels")
                
                # Get stream URL
                stream_url = await self.get_stream_url(page, channel['id'])
                
                if stream_url:
                    channel['stream_url'] = stream_url
                    channel['cookie'] = cookie
                    self.channels.append(channel)
                else:
                    # Try fallback
                    fallback = self.fallback_url(channel['name'])
                    if fallback:
                        channel['stream_url'] = fallback
                        channel['cookie'] = cookie
                        self.channels.append(channel)
            
            await browser.close()
            
            # Summary
            elapsed = (datetime.now() - start_time).total_seconds()
            working = sum(1 for c in self.channels if 'bldcmprod' in c.get('stream_url', ''))
            print(f"\n{'='*70}")
            print(f"✅ COMPLETED in {elapsed:.1f} seconds")
            print(f"   Total channels: {len(self.channels)}")
            print(f"   Streams captured: {working}")
            print(f"{'='*70}\n")

    async def get_cookie(self, page, context, channel_id: str) -> str:
        """Get Edge-Cache-Cookie from channel"""
        try:
            await page.goto(f'https://toffeelive.com/en/watch/{channel_id}', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(8000)
            
            # Check if video loaded
            video = await page.evaluate('!!document.querySelector("video")')
            if video:
                print(f"   ✓ Video loaded for {channel_id}")
            
            # Get cookies
            cookies = await context.cookies()
            for c in cookies:
                if c['name'] == 'Edge-Cache-Cookie':
                    return f"Edge-Cache-Cookie={c['value']}"
            
            return ""
        except:
            return ""

    async def get_stream_url(self, page, channel_id: str) -> str:
        """Get actual stream URL"""
        try:
            await page.goto(f'https://toffeelive.com/en/watch/{channel_id}', wait_until='networkidle', timeout=20000)
            await page.wait_for_timeout(5000)
            
            # Try to get video source
            video_src = await page.evaluate('''
                () => {
                    const video = document.querySelector('video');
                    if (video && video.src && video.src.includes('m3u8')) {
                        return video.src;
                    }
                    const source = document.querySelector('source');
                    if (source && source.src && source.src.includes('m3u8')) {
                        return source.src;
                    }
                    return null;
                }
            ''')
            
            if video_src:
                return video_src
            
            # Try to get from network
            m3u8_url = await page.evaluate('''
                () => {
                    const perf = performance.getEntriesByType('resource');
                    for (let entry of perf) {
                        if (entry.name.includes('m3u8')) {
                            return entry.name;
                        }
                    }
                    return null;
                }
            ''')
            
            return m3u8_url
            
        except:
            return None

    def fallback_url(self, channel_name: str) -> str:
        """Construct fallback URL"""
        # Special mappings
        special = {
            'Ekattor TV': 'ekattor_tv',
            'Somoy TV': 'somoy_tv',
            'Jamuna TV': 'jamuna_tv',
            'Asian TV': 'asian_tv',
            'Bangla TV': 'bangla_tv',
            'Independent TV': 'independent_tv',
            'Channel i': 'channel_i',
            'Global TV': 'global_tv',
        }
        
        slug = special.get(channel_name, channel_name.lower().replace(' ', '_'))
        return f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{slug}/playlist.m3u8"

    def generate_files(self):
        """Generate output files"""
        now = datetime.now()
        
        # OTT Navigator format
        ott_lines = [
            '#EXTM3U',
            f'# By @kgkaku',
            f'# Scrapped on {now.strftime("%Y_%m_%d")} {now.strftime("%H:%M:%S")}',
            f'# Total channels: {len(self.channels)}',
            ''
        ]
        
        # NSPlayer format (pure JSON)
        ns_lines = [
            '#EXTM3U',
            f'# By @kgkaku',
            f'# Scrapped on {now.strftime("%Y_%m_%d")} {now.strftime("%H:%M:%S")}',
            f'# Total channels: {len(self.channels)}',
            ''
        ]
        
        for ch in self.channels:
            # OTT format
            ott_lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}", {ch["name"]}')
            ott_lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            if ch.get('cookie'):
                ott_lines.append(f'#EXTHTTP:{{"cookie":"{ch["cookie"]}"}}')
            ott_lines.append(ch['stream_url'])
            ott_lines.append('')
            
            # NSPlayer format - pure JSON
            channel_json = {
                "name": ch['name'],
                "link": ch['stream_url'],
                "logo": ch['logo'],
                "cookie": ch.get('cookie', '')
            }
            ns_lines.append(f'#EXTINF:-1,{json.dumps(channel_json, ensure_ascii=False)}')
            ns_lines.append(ch['stream_url'])
            ns_lines.append('')
        
        # Save files
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write('\n'.join(ott_lines))
        
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            f.write('\n'.join(ns_lines))
        
        # Save JSON
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": now.isoformat(),
                "total_channels": len(self.channels),
                "channels": self.channels
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Files saved: {len(self.channels)} channels")
        print(f"   - toffee-ott-navigator.m3u")
        print(f"   - toffee-nsplayer.m3u")
        print(f"   - toffee.json")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.generate_files()

if __name__ == "__main__":
    asyncio.run(main())
