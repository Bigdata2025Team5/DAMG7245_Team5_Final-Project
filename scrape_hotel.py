import asyncio
import os
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
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(3000)

    # Click "View more hotels" to load all listings
    while True:
        try:
            await page.click("a.cmp-button--view-more", timeout=3000)
            await page.wait_for_timeout(2000)
        except:
            break

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div[data-component-hotelcard]")

    for card in cards:
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

        except Exception as e:
            print(f"⚠️ Error in {city} hotel card: {e}")

    return hotels

async def scrape_all_cities():
    all_hotels = []
    async with async_playwright() as p:
        # Install browsers if needed
        try:
            await p.chromium.launch(headless=True)
        except:
            import subprocess
            subprocess.run(['playwright', 'install', 'chromium'])
        
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for city, url in CITY_URLS.items():
            print(f"🏙️ Scraping {city}...")
            city_hotels = await scrape_city_hotels(page, city, url)
            all_hotels.extend(city_hotels)
            print(f"  Found {len(city_hotels)} hotels in {city}")

        await browser.close()

    return all_hotels

async def main():
    print("Starting hotel data scraping...")
    hotels = await scrape_all_cities()
    
    # Save to CSV
    df = pd.DataFrame(hotels)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"✅ Raw data saved to {RAW_DATA_PATH}")
    print(f"  Total hotels scraped: {len(df)}")

if __name__ == "__main__":
    asyncio.run(main())