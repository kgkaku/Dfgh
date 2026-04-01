import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []
        self.seen_ids = set()  # avoid duplicates

    async def capture_m3u8_url(self, page, timeout=15000):
        """Capture .m3u8 request URL from network"""
        m3u8_url = None
        def handle_request(request):
            nonlocal m3u8_url
            if '.m3u8' in request.url:
                m3u8_url = request.url
        page.on('request', handle_request)
        try:
            await page.wait_for_timeout(3000)  # let network settle
        finally:
            page.remove_listener('request', handle_request)
        return m3u8_url

    async def scrape(self):
        start_time = datetime.now()
        print("\n" + "="*70)
        print("TOFFEE LIVE CHANNEL SCRAPER (OPTIMIZED)")
        print("Created by @kgkaku")
        print("="*70 + "\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Toffee (Linux;Android 14)'
            )
            page = await context.new_page()

            # STEP 1: Load live page and scroll to load ALL channels
            print("📡 Loading channels...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=8000)
            
            # Aggressive scrolling
            prev_count = 0
            for scroll in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                current = await page.evaluate('document.querySelectorAll(\'a[href*="/watch/"]\').length')
                print(f"   Scroll {scroll+1}: {current} channels")
                if current == prev_count:
                    break
                prev_count = current
            
            # Get ALL channel links
            links = await page.query_selector_all('a[href*="/watch/"]')
            print(f"\n   ✓ Found {len(links)} channel links")
            
            # Extract ALL channels
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
                    
                    name = ' '.join(name.split())
                    
                    if channel_id not in channels_dict:
                        channels_dict[channel_id] = {
                            'id': channel_id,
                            'name': name if name else channel_id,
                            'logo': logo
                        }
            
            channels_list = list(channels_dict.values())
            print(f"   ✓ Unique channels: {len(channels_list)}")
            
            # STEP 2: Get UNIQUE cookie and real stream URL for each channel
            print("\n🍪 Capturing UNIQUE cookies & stream URLs for each channel...\n")
            
            for idx, channel in enumerate(channels_list):
                print(f"[{idx+1}/{len(channels_list)}] {channel['name']}")
                retry = 2
                success = False
                
                while retry > 0 and not success:
                    try:
                        # Visit channel watch page
                        await page.goto(f'https://toffeelive.com/en/watch/{channel["id"]}', wait_until='domcontentloaded', timeout=30000)
                        
                        # Wait for video element or source
                        try:
                            await page.wait_for_selector('video[src], source[src]', timeout=8000)
                        except:
                            pass  # maybe still loading
                        
                        # Capture m3u8 URL from network
                        stream_url = await self.capture_m3u8_url(page, timeout=5000)
                        
                        if not stream_url:
                            # fallback: look in DOM
                            stream_url = await page.evaluate('''
                                () => {
                                    const video = document.querySelector('video');
                                    if (video && video.src) return video.src;
                                    const source = document.querySelector('source');
                                    if (source && source.src) return source.src;
                                    return null;
                                }
                            ''')
                        
                        # Get cookies for this specific channel
                        cookies = await context.cookies()
                        edge_cookie = None
                        for c in cookies:
                            if c['name'] == 'Edge-Cache-Cookie':
                                edge_cookie = f"Edge-Cache-Cookie={c['value']}"
                                break
                        
                        if stream_url and edge_cookie:
                            # Verify cookie domain matches URL domain
                            if 'bldcmprod' in stream_url and 'bldcmprod' in edge_cookie:
                                success = True
                            elif 'mprod' in stream_url and 'mprod' in edge_cookie:
                                success = True
                            else:
                                # Mismatch: try to fix
                                print(f"   ⚠️ Domain mismatch for {channel['name']}, retrying...")
                                retry -= 1
                                await asyncio.sleep(1)
                                continue
                        else:
                            # Could not get either, retry
                            retry -= 1
                            await asyncio.sleep(1)
                            continue
                        
                        # Store channel data
                        self.channels.append({
                            'name': channel['name'],
                            'link': stream_url,
                            'logo': channel['logo'],
                            'cookie': edge_cookie
                        })
                        print(f"   ✅ OK")
                        success = True
                        
                    except Exception as e:
                        print(f"   ❌ Error: {str(e)[:60]}")
                        retry -= 1
                        if retry == 0:
                            # Last attempt: construct fallback URL but keep cookie if possible
                            fallback_url = self.construct_fallback_url(channel)
                            if fallback_url:
                                self.channels.append({
                                    'name': channel['name'],
                                    'link': fallback_url,
                                    'logo': channel['logo'],
                                    'cookie': edge_cookie if edge_cookie else ''
                                })
                                print(f"   🟡 Fallback used")
                            else:
                                print(f"   ⏭️ Skipped (no fallback)")
                        else:
                            await asyncio.sleep(2)
            
            await browser.close()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            with_cookie = sum(1 for c in self.channels if c.get('cookie'))
            print(f"\n{'='*70}")
            print(f"✅ COMPLETED in {elapsed:.1f} seconds")
            print(f"Total channels: {len(self.channels)}")
            print(f"Channels with cookie: {with_cookie}")
            print(f"{'='*70}\n")
    
    def construct_fallback_url(self, channel):
        """Construct URL based on channel name pattern"""
        name = channel['name'].lower()
        # Event channels
        if 'epl' in name or 'premier league' in name:
            # Try to extract number
            match = re.search(r'(\d+)', name)
            if match:
                num = match.group(1)
                return f"https://mprod-cdn.toffeelive.com/live/match-{num}/index.m3u8"
            else:
                return None
        elif 'bfl' in name or 'bangladesh' in name:
            match = re.search(r'(\d+)', name)
            if match:
                num = match.group(1)
                # BFL match numbers start from 11 in observed data
                return f"https://mprod-cdn.toffeelive.com/live/match-{int(num)+10}/index.m3u8"
            else:
                return None
        else:
            # Regular channel
            slug = re.sub(r'[^a-z0-9]+', '_', name).strip('_')
            # Special mapping for known variations
            mapping = {
                'cartoon_network': 'cartoon_network_sd',
                'animal_planet': 'animal_planet_sd',
                'tlc': 'tlc_sd',
                'discovery': 'discovery_sd',
                'pogo': 'pogo_sd',
                'zing': 'zing_sd',
                'sony_yay': 'sonyyay',
                'sony_aath': 'sonyaath',
                'hum': 'hum_tv',
                'hum_masala': 'hum_masala',
                'hum_sitaray': 'hum_sitaray',
                'sony_ten_sports_1_hd': 'sony_sports_1_hd',
                'sony_ten_sports_2_hd': 'sony_sports_2_hd',
                'sony_ten_sports_5_hd': 'sony_sports_5_hd',
                'sony_bbc_earth_hd': 'sonybbc_earth_hd',
                'sony_entertainment_television_hd': 'sonyentertainmnt_hd',
                'sony_sab_hd': 'sonysab_hd',
                'zee_bangla': 'zee_bangla',
                'zee_anmol': 'zee_anmol',
                'zee_tv_hd': 'zee_tv_hd',
                'zee_cinema_hd': 'zee_cinema_hd',
                'b4u_music': 'b4u_music',
                'b4u_movies': 'b4u_movies',
                'and_tv_hd': 'and_tv_hd',
                'and_pictures_hd': 'andpicture_hd',
                'cartoon_network_hd_': 'cartoon_network_hd',
                'discovery_kids': 'discovery_kids',
                'discovery_science': 'discovery_science',
                'discovery_turbo': 'discovery_turbo',
                'investigation_discovery_hd': 'discovary_investigation_hd',
                'tlc_hd': 'tlc_hd',
                'animal_planet_hd': 'animal_planet_hd',
                'epl_channel_1': 'epl_channel_1',
                'epl_channel_2': 'epl_channel_2',
                'epl_channel_3': 'epl_channel_3',
                'epl_channel_4': 'epl_channel_4',
                'epl_channel_5': 'epl_channel_5',
                'epl_channel_6': 'epl_channel_6',
                'bfl__live_1': 'bfl__live_1',
                'bfl__live_2': 'bfl__live_2',
                'bfl__live_3': 'bfl__live_3',
                'bfl__live_4': 'bfl__live_4'
            }
            slug = mapping.get(slug, slug)
            return f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{slug}/playlist.m3u8"

    def generate_files(self):
        """Generate output files with pure JSON array for NSPlayer"""
        now = datetime.now()
        timestamp = now.strftime("%Y_%m_%d")
        time = now.strftime("%H:%M:%S")
        
        # toffee-ott-navigator.m3u (standard M3U)
        ott_lines = [
            '#EXTM3U',
            f'# Created by @kgkaku',
            f'# Scraped on {timestamp} at {time}',
            f'# Total channels: {len(self.channels)}',
            ''
        ]
        
        for ch in self.channels:
            ott_lines.append(f'#EXTINF:-1 tvg-id="{ch["name"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}", {ch["name"]}')
            ott_lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            if ch.get('cookie'):
                ott_lines.append(f'#EXTHTTP:{{"cookie":"{ch["cookie"]}"}}')
            ott_lines.append(ch['link'])
            ott_lines.append('')
        
        # toffee-nsplayer.m3u - pure JSON array (like file A)
        nsplayer_array = []
        for ch in self.channels:
            nsplayer_array.append({
                "name": ch['name'],
                "link": ch['link'],
                "logo": ch['logo'],
                "cookie": ch.get('cookie', '')
            })
        
        # toffee.json - complete data with metadata
        json_data = {
            "created_by": "@kgkaku",
            "generated_at": now.isoformat(),
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        
        # Save files
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write('\n'.join(ott_lines))
        
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            json.dump(nsplayer_array, f, indent=2, ensure_ascii=False)
        
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Files saved:")
        print(f"   toffee-ott-navigator.m3u - {len(self.channels)} channels")
        print(f"   toffee-nsplayer.m3u - {len(self.channels)} channels (Pure JSON array)")
        print(f"   toffee.json - {len(self.channels)} channels (Complete data)")
        print(f"\n✨ Created by @kgkaku")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.generate_files()

if __name__ == "__main__":
    asyncio.run(main())
