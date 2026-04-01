import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []
    
    async def scrape(self):
        start_time = datetime.now()
        print("\n" + "="*70)
        print("TOFFEE LIVE CHANNEL SCRAPER")
        print("="*70 + "\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Go to live page
            print("Loading live page...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=30000)
            
            # Wait for content
            await page.wait_for_timeout(5000)
            
            # Scroll to load all channels
            for i in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
            
            # Get all channel links - try different selectors
            links = await page.query_selector_all('a[href*="/watch/"]')
            if not links:
                links = await page.query_selector_all('a[href*="watch"]')
            if not links:
                links = await page.query_selector_all('.channel-item a, .program-item a')
            
            print(f"Found {len(links)} channel links")
            
            # Process each channel
            for idx, link in enumerate(links[:30]):  # Limit to 30 for testing
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    
                    channel_id = href.split('/watch/')[-1].split('?')[0]
                    
                    # Get name from image alt or text
                    img = await link.query_selector('img')
                    if img:
                        name = await img.get_attribute('alt') or ''
                        logo = await img.get_attribute('src') or ''
                    else:
                        name = await link.text_content() or channel_id
                        logo = ''
                    
                    name = name.strip()
                    if not name:
                        name = channel_id
                    
                    print(f"[{idx+1}] {name}")
                    
                    # Visit channel page to get stream URL and cookie
                    await page.goto(f'https://toffeelive.com/en/watch/{channel_id}', timeout=30000)
                    await page.wait_for_timeout(3000)
                    
                    # Get m3u8 URL from network
                    m3u8_url = None
                    async def on_response(response):
                        nonlocal m3u8_url
                        if '.m3u8' in response.url:
                            m3u8_url = response.url
                    
                    page.on('response', on_response)
                    await page.wait_for_timeout(2000)
                    
                    # Get cookie
                    cookies = await context.cookies()
                    edge_cookie = None
                    for c in cookies:
                        if c['name'] == 'Edge-Cache-Cookie':
                            edge_cookie = f"Edge-Cache-Cookie={c['value']}"
                            break
                    
                    if m3u8_url and edge_cookie:
                        self.channels.append({
                            'name': name,
                            'link': m3u8_url,
                            'logo': logo,
                            'cookie': edge_cookie
                        })
                        print(f"  ✓ OK")
                    else:
                        print(f"  ✗ Failed (no stream/cookie)")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)[:50]}")
                    continue
            
            await browser.close()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*70}")
            print(f"Completed in {elapsed:.1f} seconds")
            print(f"Total channels: {len(self.channels)}")
            print(f"{'='*70}\n")
    
    def generate_files(self):
        """Generate output files"""
        # Pure JSON array for NSPlayer
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            json.dump([{
                "name": ch['name'],
                "link": ch['link'],
                "logo": ch['logo'],
                "cookie": ch['cookie']
            } for ch in self.channels], f, indent=2, ensure_ascii=False)
        
        # M3U format
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n\n')
            for ch in self.channels:
                f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}", {ch["name"]}\n')
                if ch.get('cookie'):
                    f.write(f'#EXTHTTP:{{"cookie":"{ch["cookie"]}"}}\n')
                f.write(f'{ch["link"]}\n\n')
        
        print(f"Files saved: {len(self.channels)} channels")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.generate_files()

if __name__ == "__main__":
    asyncio.run(main())
