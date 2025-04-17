import asyncio
import os
import random
import time
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Define output path for data
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_DATA_PATH = os.path.join(OUTPUT_DIR, 'multi_city_ihg_hotels.csv')

# Define the city URLs for scraping
CITY_URLS = {
    "New York": "https://www.ihg.com/new-york-city-new-york",
    "San Francisco": "https://www.ihg.com/san-francisco-california",
    "Chicago": "https://www.ihg.com/chicago-illinois",
    "Seattle": "https://www.ihg.com/seattle-washington",
    "Las Vegas": "https://www.ihg.com/las-vegas-nevada",
    "Los Angeles": "https://www.ihg.com/los-angeles-california"
}

async def scrape_city_hotels(page, city, url):
    hotels = []
    print(f"  Navigating to {url}...")
    
    # Add random delay before navigation to appear more human-like
    await asyncio.sleep(random.uniform(1, 3))
    
    # Navigate to URL
    await page.goto(url, timeout=90000, wait_until="networkidle")
    print(f"  Page loaded for {city}")
    
    # Wait for content to fully load
    await page.wait_for_selector("div[data-component-hotelcard]", timeout=30000)
    print(f"  Hotel cards found for {city}")
    
    # Add additional wait to ensure JavaScript is fully loaded
    await asyncio.sleep(3)
    
    # Click "View more hotels" to load all listings
    view_more_count = 0
    while True:
        try:
            # Check if button exists
            view_more_button = await page.query_selector("a.cmp-button--view-more")
            if not view_more_button:
                print("  No more 'View more' buttons found")
                break
            
            # Wait a bit before clicking (human-like behavior)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Scroll button into view and click
            await view_more_button.scroll_into_view_if_needed()
            await view_more_button.click()
            view_more_count += 1
            print(f"  Clicked 'View more' button ({view_more_count} times)")
            
            # Wait for new content to load
            await asyncio.sleep(3)
        except Exception as e:
            print(f"  No more 'View more' buttons or error: {e}")
            break

    print(f"  Extracting hotel data from page...")
    
    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0);")
    await asyncio.sleep(1)
    
    # Get HTML content
    html = await page.content()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div[data-component-hotelcard]")
    print(f"  Found {len(cards)} hotel cards on page")

    for card_index, card in enumerate(cards):
        try:
            name_tag = card.select_one("h4.cmp-card__title a")
            name = name_tag.text.strip() if name_tag else "N/A"
            link = name_tag["href"] if name_tag else "N/A"

            # Image fix: Prefer `data-cmp-src` if available
            image_div = card.select_one("div[data-cmp-is='image']")
            image = image_div.get("data-cmp-src") if image_div else None
            if not image:
                image_tag = card.select_one("img.cmp-image__image")
                image = image_tag["src"] if image_tag else "N/A"

            address = card.select_one("address.cmp-card__address")
            address = address.text.strip().replace("\n", ", ") if address else "N/A"
            distance = card.select_one("span.cmp-card__distance-text")
            distance = distance.text.strip() if distance else "N/A"
            rating = card.select_one("span.cmp-card__rating-count")
            rating = rating.text.strip() if rating else "N/A"
            reviews = card.select("a.cmp-card__rating-count")
            reviews = reviews[-1].text.strip() if reviews else "N/A"
            price = card.select_one("span.cmp-card__hotel-price-value")
            price = price.text.strip() if price else "N/A"
            currency = card.select_one("abbr.cmp-card__hotel-price-currency")
            currency = currency.text.strip() if currency else "USD"
            room_fees = card.select_one("p.cmp-card__room-fees")
            room_fees = room_fees.text.strip() if room_fees else "N/A"
            exclusions = card.select_one("p.cmp-card__exclusions")
            exclusions = exclusions.text.strip() if exclusions else "N/A"
            badge = card.select_one("span.cmp-card__flag-prop-text")
            certification = badge.text.strip() if badge else "N/A"

            hotels.append({
                "City": city,
                "Name": name,
                "Link": link,
                "Image": image,
                "Address": address,
                "Distance": distance,
                "Rating": rating,
                "Reviews": reviews,
                "Price (per night)": f"{currency} {price}",
                "Room Fees": room_fees,
                "Exclusions": exclusions,
                "Certified": certification
            })
            
            if (card_index + 1) % 5 == 0 or card_index == len(cards) - 1:
                print(f"  Processed {card_index + 1}/{len(cards)} hotels")

        except Exception as e:
            print(f"⚠️ Error in {city} hotel card #{card_index + 1}: {e}")

    return hotels

async def main():
    print("=" * 50)
    print("IHG HOTELS DATA SCRAPING")
    print("=" * 50)
    print("Starting hotel data scraping process...")
    print(f"Will save data to: {RAW_DATA_PATH}")
    
    all_hotels = []
    
    try:
        # Set to True for headless operation in GitHub Actions
        # Set to False for local debugging
        HEADLESS_MODE = True  # Change to False for local development if needed
        
        print(f"Browser mode: {'Headless' if HEADLESS_MODE else 'Visible'}")
        
        async with async_playwright() as p:
            # Launch browser with settings to help avoid detection
            browser = await p.chromium.launch(
                headless=HEADLESS_MODE,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--disable-extensions',
                    '--window-size=1920,1080'
                ]
            )
            
            # Create context with specific user agent and viewport
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            
            # Add additional headers to appear more like a regular browser
            await context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="123", "Chromium";v="123"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            })
            
            # Create page from context
            page = await context.new_page()
            
            # Emulate human-like behavior by adding a short delay
            await asyncio.sleep(random.uniform(1, 3))
            
            # Set longer timeouts
            page.set_default_timeout(60000)
            
            # Process limited cities for faster testing
            # In production, use all cities
            cities_to_scrape = CITY_URLS
            
            # For debugging, you can limit to just a few cities
            # cities_to_scrape = {k: CITY_URLS[k] for k in ["Las Vegas", "New York"]}
            
            for city, url in cities_to_scrape.items():
                print(f"\n🏙️ Scraping {city}...")
                try:
                    city_hotels = await scrape_city_hotels(page, city, url)
                    all_hotels.extend(city_hotels)
                    print(f"  ✓ Found {len(city_hotels)} hotels in {city}")
                except Exception as e:
                    print(f"  ❌ Error scraping {city}: {str(e)}")
                    continue
            
            await browser.close()
            
        # Create DataFrame with the scraped data
        if all_hotels:
            df = pd.DataFrame(all_hotels)
            print(f"Successfully created DataFrame with {len(df)} hotels")
            
            # Save to CSV
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            df.to_csv(RAW_DATA_PATH, index=False)
            print(f"✅ Raw data saved to {RAW_DATA_PATH}")
            print(f"  Total hotels scraped: {len(df)}")
        else:
            print("❌ No hotels were scraped")
            # Create empty dataframe with expected columns
            df = pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                                     "Rating", "Reviews", "Price (per night)", "Room Fees", 
                                     "Exclusions", "Certified"])
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            df.to_csv(RAW_DATA_PATH, index=False)
            print(f"Created empty file at {RAW_DATA_PATH}")
            
    except Exception as e:
        print(f"❌ Error running the scraper: {e}")
        import traceback
        traceback.print_exc()
        
        # Create empty file in case of errors
        df = pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                                 "Rating", "Reviews", "Price (per night)", "Room Fees", 
                                 "Exclusions", "Certified"])
        os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
        df.to_csv(RAW_DATA_PATH, index=False)
        print(f"Created empty file at {RAW_DATA_PATH} after error")

if __name__ == "__main__":
    asyncio.run(main())
