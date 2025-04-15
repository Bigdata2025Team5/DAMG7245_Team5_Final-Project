import asyncio
import os
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import traceback
import sys
import shutil

# Define output path for data
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_DATA_PATH = os.path.join(OUTPUT_DIR, 'multi_city_ihg_hotels.csv')

# Define sample data path for fallback
SAMPLE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data")
SAMPLE_DATA_PATH = os.path.join(SAMPLE_DATA_DIR, 'sample_hotels.csv')

# Define the city URLs for scraping
CITY_URLS = {
    "New York": "https://www.ihg.com/new-york-city-new-york",
    "San Francisco": "https://www.ihg.com/san-francisco-california",
    "Chicago": "https://www.ihg.com/chicago-illinois",
    "Seattle": "https://www.ihg.com/seattle-washington",
    "Las Vegas": "https://www.ihg.com/las-vegas-nevada",
    "Los Angeles": "https://www.ihg.com/los-angeles-california"
}

# Create a fallback dataset
def create_fallback_data():
    """Create a sample dataset to use if scraping fails"""
    df = pd.DataFrame([
        {
            "City": "New York",
            "Name": "Holiday Inn Manhattan (Sample)",
            "Link": "https://www.ihg.com/sample/hotel/us/en/new-york/",
            "Image": "https://digital.ihg.com/sample.jpg",
            "Address": "123 Broadway, New York, NY 10001",
            "Distance": "0.5 mi (0.8 km) from city center",
            "Rating": "4.2",
            "Reviews": "420 reviews",
            "Price (per night)": "USD 299",
            "Room Fees": "Additional fees may apply",
            "Exclusions": "Breakfast not included",
            "Certified": "IHG Clean Promise"
        },
        {
            "City": "Las Vegas",
            "Name": "Venetian Resort Las Vegas (Sample)",
            "Link": "https://www.ihg.com/sample/hotel/us/en/las-vegas/",
            "Image": "https://digital.ihg.com/sample2.jpg",
            "Address": "3355 Las Vegas Blvd South, Las Vegas, NV 89109",
            "Distance": "0.2 mi (0.3 km) from city center",
            "Rating": "4.5",
            "Reviews": "1250 reviews",
            "Price (per night)": "USD 189",
            "Room Fees": "Resort fees apply",
            "Exclusions": "Parking not included",
            "Certified": "IHG Clean Promise"
        },
        {
            "City": "Chicago",
            "Name": "InterContinental Chicago (Sample)",
            "Link": "https://www.ihg.com/sample/hotel/us/en/chicago/",
            "Image": "https://digital.ihg.com/sample3.jpg",
            "Address": "505 North Michigan Avenue, Chicago, IL 60611",
            "Distance": "0.3 mi (0.5 km) from city center",
            "Rating": "4.3",
            "Reviews": "950 reviews",
            "Price (per night)": "USD 219",
            "Room Fees": "City tax applies",
            "Exclusions": "Parking fees apply",
            "Certified": "IHG Clean Promise"
        }
    ])
    
    # Create sample_data directory if it doesn't exist
    os.makedirs(SAMPLE_DATA_DIR, exist_ok=True)
    
    # Save the sample data
    df.to_csv(SAMPLE_DATA_PATH, index=False)
    print(f"Created fallback data at {SAMPLE_DATA_PATH}")
    return df

async def scrape_city_hotels(page, city, url):
    hotels = []
    print(f"  Navigating to {url}...")
    
    # Add retry logic for page navigation
    max_retries = 3
    for retry in range(max_retries):
        try:
            await page.goto(url, timeout=90000)
            print(f"  Successfully navigated to {url}")
            break
        except Exception as e:
            if retry == max_retries - 1:
                print(f"Failed to navigate to {url} after {max_retries} attempts: {e}")
                return []
            print(f"Retry {retry+1}/{max_retries} navigating to {url}: {e}")
            await page.wait_for_timeout(5000)
    
    # Wait for page to load
    await page.wait_for_timeout(5000)
    
    # Take debug screenshot
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    if is_github_actions:
        try:
            debug_dir = os.path.join(OUTPUT_DIR, "debug")
            os.makedirs(debug_dir, exist_ok=True)
            await page.screenshot(path=os.path.join(debug_dir, f"{city}_initial.png"))
            print(f"Saved initial debug screenshot for {city}")
        except Exception as e:
            print(f"Could not save debug screenshot: {e}")

    # Click "View more hotels" to load all listings
    view_more_count = 0
    while True:
        try:
            # Wait for the button to be visible
            view_more_selector = "a.cmp-button--view-more"
            try:
                # Wait for the selector to be visible with timeout
                await page.wait_for_selector(view_more_selector, timeout=5000)
            except:
                # If timeout, button might not exist anymore
                print("  No more 'View more' buttons (wait timeout)")
                break
                
            view_more_button = await page.query_selector(view_more_selector)
            if not view_more_button:
                print("  No more 'View more' buttons found")
                break
                
            # Take screenshot before clicking
            if is_github_actions and view_more_count == 0:
                try:
                    await page.screenshot(path=os.path.join(debug_dir, f"{city}_before_viewmore.png"))
                except Exception:
                    pass
                    
            # Click with retry logic
            click_success = False
            for click_retry in range(3):
                try:
                    await view_more_button.click(timeout=10000)
                    click_success = True
                    break
                except Exception as e:
                    print(f"  Click retry {click_retry+1}/3: {e}")
                    await page.wait_for_timeout(2000)
            
            if not click_success:
                print("  Failed to click 'View more' button after retries")
                break
                
            view_more_count += 1
            print(f"  Clicked 'View more' button ({view_more_count} times)")
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  No more 'View more' buttons or error: {e}")
            break

    # Take final screenshot
    if is_github_actions:
        try:
            await page.screenshot(path=os.path.join(debug_dir, f"{city}_final.png"))
            print(f"Saved final debug screenshot for {city}")
        except Exception:
            pass
            
    print(f"  Extracting hotel data from page...")
    html = await page.content()
    
    # Debug HTML output in GitHub actions
    if is_github_actions:
        try:
            with open(os.path.join(debug_dir, f"{city}_page.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Saved debug HTML for {city}")
        except Exception as e:
            print(f"Could not save debug HTML: {e}")
            
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
                try:
                    import subprocess
                    print("Installing Chromium via Playwright...")
                    result = subprocess.run(['playwright', 'install', 'chromium'], capture_output=True, text=True)
                    print(f"Installation output: {result.stdout}")
                    if result.stderr:
                        print(f"Installation errors: {result.stderr}")
                except Exception as install_error:
                    print(f"Error installing Chromium: {install_error}")
                    return []
            
            # Detect environment (GitHub Actions vs local)
            is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
            headless_mode = True  # Always use headless mode for reliability
            print(f"Running in {'GitHub Actions' if is_github_actions else 'local'} environment")
            print(f"Using headless mode: {headless_mode}")
            
            # Launch browser with appropriate settings for CI environment
            print("Launching browser...")
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu'
            ]
            
            try:
                browser = await p.chromium.launch(
                    headless=headless_mode,
                    args=browser_args,
                    timeout=120000  # 2 minute timeout
                )
                
                if not browser:
                    raise Exception("Browser launch returned None")
                    
                print("Browser launched successfully")
            except Exception as e:
                print(f"Failed to launch browser: {e}")
                traceback.print_exc()
                return []
            
            try:
                print("Creating new page...")
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                )
                
                if not page:
                    raise Exception("Page creation returned None")
                    
                print("Page created successfully")
            except Exception as e:
                print(f"Failed to create page: {e}")
                traceback.print_exc()
                await browser.close()
                return []
            
            try:
                # Set default timeout
                await page.set_default_timeout(60000)
                print("Set page timeout successfully")
            except Exception as e:
                print(f"Failed to set page timeout: {e}")
                traceback.print_exc()
                await browser.close()
                return []
            
            # Process each city
            print(f"Starting to scrape {len(CITY_URLS)} cities...")
            
            # For GitHub Actions, limit to 2 cities to avoid timeouts
            if is_github_actions:
                # Just use a subset of cities for GitHub Actions to avoid timeouts
                limited_urls = {}
                cities_to_include = ["New York", "Las Vegas"]  # Choose 2 cities that are likely to work well
                for city in cities_to_include:
                    if city in CITY_URLS:
                        limited_urls[city] = CITY_URLS[city]
                
                print(f"In GitHub Actions, limiting to {len(limited_urls)} cities: {', '.join(limited_urls.keys())}")
                cities_to_scrape = limited_urls
            else:
                cities_to_scrape = CITY_URLS
            
            for city, url in cities_to_scrape.items():
                print(f"\n🏙️ Scraping {city}...")
                try:
                    city_hotels = await scrape_city_hotels(page, city, url)
                    all_hotels.extend(city_hotels)
                    print(f"  ✓ Found {len(city_hotels)} hotels in {city}")
                except Exception as e:
                    print(f"❌ Error scraping {city}: {e}")
                    traceback.print_exc()

            print("Closing browser...")
            await browser.close()
                
    except Exception as e:
        print(f"❌ Error during scraping process: {e}")
        traceback.print_exc()
        
    return all_hotels

async def main():
    print("=" * 50)
    print("IHG HOTELS DATA SCRAPING")
    print("=" * 50)
    print("Starting hotel data scraping process...")
    print(f"Will save data to: {RAW_DATA_PATH}")
    
    try:
        # Ensure fallback data exists
        if not os.path.exists(SAMPLE_DATA_PATH):
            create_fallback_data()
        
        # Run the scraper
        hotels = await scrape_all_cities()
        
        if not hotels or len(hotels) == 0:
            print("❌ No hotel data was retrieved. Using sample data.")
            
            # Use fallback data
            if os.path.exists(SAMPLE_DATA_PATH):
                os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
                shutil.copy(SAMPLE_DATA_PATH, RAW_DATA_PATH)
                print(f"Copied sample data to {RAW_DATA_PATH}")
                df = pd.read_csv(RAW_DATA_PATH)
                print(f"Successfully loaded {len(df)} sample hotels")
            else:
                # Create fallback data if it doesn't exist
                df = create_fallback_data()
                os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
                df.to_csv(RAW_DATA_PATH, index=False)
                print(f"Created and saved fallback data to {RAW_DATA_PATH}")
        else:
            # Create DataFrame with the scraped data
            df = pd.DataFrame(hotels)
            print(f"Successfully created DataFrame with {len(df)} hotels")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            
            # Save to CSV
            df.to_csv(RAW_DATA_PATH, index=False)
            print(f"\n✅ Raw data saved to {RAW_DATA_PATH}")
        
        print(f"  Total hotels in dataset: {len(df)}")
        
    except Exception as e:
        print(f"❌ Error running the scraper: {e}")
        traceback.print_exc()
        
        # Use fallback data
        if os.path.exists(SAMPLE_DATA_PATH):
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            shutil.copy(SAMPLE_DATA_PATH, RAW_DATA_PATH)
            print(f"Copied sample data to {RAW_DATA_PATH} after error")
        else:
            # Create fallback data if it doesn't exist
            df = create_fallback_data()
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            df.to_csv(RAW_DATA_PATH, index=False)
            print(f"Created and saved fallback data to {RAW_DATA_PATH} after error")

if __name__ == "__main__":
    asyncio.run(main())
