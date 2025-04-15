import asyncio
import os
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Define output path for data
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_DATA_PATH = os.path.join(OUTPUT_DIR, 'multi_city_ihg_hotels.csv')
# Make sure the data directory exists
os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
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
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(3000)

    # Click "View more hotels" to load all listings
    view_more_count = 0
    while True:
        try:
            view_more_button = await page.query_selector("a.cmp-button--view-more")
            if not view_more_button:
                break
                
            await view_more_button.click(timeout=3000)
            view_more_count += 1
            print(f"  Clicked 'View more' button ({view_more_count} times)")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  No more 'View more' buttons or error: {e}")
            break

    print(f"  Extracting hotel data from page...")
    html = await page.content()
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

async def scrape_all_cities():
    all_hotels = []
    
    try:
        print("Initializing Playwright...")
        async with async_playwright() as p:
            # Install browsers if needed
            try:
                print("Checking Chromium installation...")
                browser_test = await p.chromium.launch(headless=True)
                await browser_test.close()
                print("Chromium is properly installed")
            except Exception as e:
                print(f"Need to install Chromium: {e}")
                import subprocess
                print("Installing Chromium via Playwright...")
                result = subprocess.run(['playwright', 'install', 'chromium'], capture_output=True, text=True)
                print(f"Installation output: {result.stdout}")
                if result.stderr:
                    print(f"Installation errors: {result.stderr}")
            
            # Detect environment (GitHub Actions vs local)
            is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
            headless_mode = True if is_github_actions else False
            print(f"Running in {'GitHub Actions' if is_github_actions else 'local'} environment")
            print(f"Using headless mode: {headless_mode}")
            
            # Launch browser 
            print("Launching browser...")
            browser = await p.chromium.launch(headless=headless_mode)
            
            print("Creating new page...")
            page = await browser.new_page()
            
            # Process each city
            print(f"Starting to scrape {len(CITY_URLS)} cities...")
            for city, url in CITY_URLS.items():
                print(f"\n🏙️ Scraping {city}...")
                city_hotels = await scrape_city_hotels(page, city, url)
                all_hotels.extend(city_hotels)
                print(f"  ✓ Found {len(city_hotels)} hotels in {city}")

            print("Closing browser...")
            await browser.close()
                
    except Exception as e:
        print(f"❌ Error during scraping process: {e}")
        import traceback
        traceback.print_exc()
        
    return all_hotels

async def main():
    print("=" * 50)
    print("IHG HOTELS DATA SCRAPING")
    print("=" * 50)
    print("Starting hotel data scraping process...")
    print(f"Will save data to: {RAW_DATA_PATH}")
    
    try:
        # Run the scraper
        hotels = await scrape_all_cities()
        
        if not hotels or len(hotels) == 0:
            print("❌ No hotel data was retrieved. Creating empty DataFrame.")
            df = pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                                      "Rating", "Reviews", "Price (per night)", "Room Fees", 
                                      "Exclusions", "Certified"])
        else:
            # Create DataFrame with the scraped data
            df = pd.DataFrame(hotels)
            print(f"Successfully created DataFrame with {len(df)} hotels")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
        
        # Save to CSV
        df.to_csv(RAW_DATA_PATH, index=False)
        print(f"\n✅ Raw data saved to {RAW_DATA_PATH}")
        print(f"  Total hotels scraped: {len(df)}")
        
    except Exception as e:
        print(f"❌ Error running the scraper: {e}")
        import traceback
        traceback.print_exc()
        
        # Create an empty file so the pipeline can continue
        os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
        pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                             "Rating", "Reviews", "Price (per night)", "Room Fees", 
                             "Exclusions", "Certified"]).to_csv(RAW_DATA_PATH, index=False)
        print(f"Created empty output file at {RAW_DATA_PATH} to prevent pipeline failure")

if __name__ == "__main__":
    asyncio.run(main())
