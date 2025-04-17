import os
import json
import traceback
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from datetime import date , timedelta
from typing import Literal
from litellm import completion
from decimal import Decimal
import os
from dotenv import load_dotenv

load_dotenv(override=True)
from snowflake_fetch import (
    fetch_attractions,
    fetch_hotels,
    fetch_tours,
    convert_decimal_to_float,
    get_next_closest_places
)

# Load Grok API key
os.environ["LITELLM_API_KEY"] = os.getenv("XAI_API_KEY")

# FastAPI app setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Input schema ---
class ItineraryInput(BaseModel):
    city: str
    start_date: date
    end_date: date
    preference: Literal[
        "Suggest an itinerary with Tours, Accommodation, Things to do",
        "Suggest an itinerary with Accommodation, Things to do",
        "Suggest an itinerary with Things to do"
    ]
    travel_type: Literal["Solo", "With Family"]
    adults: int = 1
    kids: int = 0
    budget: Literal["low", "medium", "high"] = "medium"

    @field_validator('end_date')
    def end_date_after_start(cls, end_date, values):
        if 'start_date' in values.data and end_date < values.data['start_date']:
            raise ValueError("End date must be after start date")
        return end_date

# --- Itinerary data fetch ---
def fetch_itinerary_data(city, start_date, end_date, preference, travel_type, adults, kids, budget):
    include_tours = "Tours" in preference
    include_accommodation = "Accommodation" in preference
    include_things = "Things to do" in preference

    return {
        "city": city,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "travel_type": travel_type,
        "adults": adults,
        "kids": kids,
        "budget": budget,
        "hotels": convert_decimal_to_float(fetch_hotels(city, budget))[:3] if include_accommodation else [],
        "tours": convert_decimal_to_float(fetch_tours(city, budget))[:6] if include_tours else [],
        "attractions": convert_decimal_to_float(fetch_attractions(city, budget, include_free=True))[:6] if include_things else []
    }

# --- Use Grok via LiteLLM ---
import random
import json
from datetime import datetime
from litellm import completion

import random
import json
from datetime import datetime
from litellm import completion

def run_crew_with_data(data):
    try:
        # Step 1: Date difference calculation
        start = datetime.strptime(data["start_date"], "%Y-%m-%d")
        end = datetime.strptime(data["end_date"], "%Y-%m-%d")
        num_days = (end - start).days + 1
        date_list = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]

        # Step 2: Get and shuffle items
        hotels = data.get("hotels", [])
        tours = data.get("tours", [])
        attractions = data.get("attractions", [])

        random.shuffle(hotels)
        random.shuffle(tours)
        random.shuffle(attractions)

        # Step 3: Repeat items to ensure sufficient data
        while len(hotels) < num_days:
            hotels += hotels
        while len(tours) < num_days * 2:
            tours += tours
        while len(attractions) < num_days * 2:
            attractions += attractions

        # Step 4: Create day-wise structured data
        days = []
        for i in range(num_days):
            day_data = {
                "day": f"Day {i+1}",
                "hotel": hotels[i % len(hotels)],
                "tours": tours[i*2:(i+1)*2],
                "attractions": attractions[i*2:(i+1)*2]
            }
            days.append(day_data)

        # Step 5: Final data format for LLM
        reduced_data = {
            "city": data["city"],
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "travel_type": data["travel_type"],
            "adults": data["adults"],
            "kids": data["kids"],
            "budget": data["budget"],
            "days": days
        }

        # Step 6: Prompt with HTML formatting instructions
        prompt = f"""
You are a travel itinerary expert.

Generate a {num_days}-day HTML travel itinerary for a trip to {data['city']} from {data['start_date']} to {data['end_date']} for {data['adults']} adults and {data['kids']} kids, traveling as {data['travel_type']} on a {data['budget']} budget.

📝 Requirements per day:
- 1 hotel (use NAME, LINK, IMAGE, ADDRESS, DISTANCE, RATING, REVIEWS, "Price (per night)",  EXCLUSIONS, CERTIFIED)
- 2 tours (use TITLE, RATING, Review Count, PRICE, Know More, ITINERARY, INCLUSIONS, EXCLUSIONS, Additional Info, Key Details,IMAGE, Short Reviews)
- 2 attractions (use Travel Tips, Ticket Details, HOURS, How to Reach, Restaurants Nearby, IMAGE, Short Description)

🖼️ Important: Display the image of each hotel, tour, and attraction using:
<img src="IMAGE_URL" alt="Title" width="300" style="border-radius: 10px; margin-bottom: 10px;" />

🧱 Output Format:
- Return raw HTML only (no backticks or Markdown).
- Use structured HTML with <div>, <h2>, <h3>, <p>, <ul>, <img>, etc.
- Use class names like "day-card", "item-section", "image-block" for styling hooks.

📦 Data:
{json.dumps(data, indent=2, default=str)}
"""

        response = completion(
            model="xai/grok-2-1212",
            messages=[{"role": "user", "content": prompt}],
            provider="grok",
            api_key=os.getenv("XAI_API_KEY")  # 👈 make sure this env variable is set
        )

        return response['choices'][0]['message']['content']

    except Exception as e:
        print("Grok call error:", e)
        raise RuntimeError("Failed to generate itinerary from Grok.")

# --- Routes ---
@app.get("/")
def root():
    return {"status": "online"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Cloud Run passes $PORT
    uvicorn.run(app, host="0.0.0.0", port=port)


@app.post("/generate-itinerary")
def generate_itinerary(payload: ItineraryInput):
    try:
        structured_data = fetch_itinerary_data(
            payload.city,
            payload.start_date,
            payload.end_date,
            payload.preference,
            payload.travel_type,
            payload.adults,
            payload.kids,
            payload.budget
        )

        html = run_crew_with_data(structured_data)

        return {
            "status": "success",
            "data": {
                "itinerary_html": html
            }
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating itinerary: {str(e)}")


@app.post("/get-alternatives")
def get_alternatives(payload: dict):
    try:
        city = payload["city"]
        category = payload["category"]
        current_url = payload["current_url"]
        budget = payload["budget"]

        # Fetch full list
        if category == "hotel":
            all_items = fetch_hotels(city, budget)
        elif category == "tour":
            all_items = fetch_tours(city, budget)
        elif category == "attraction":
            all_items = fetch_attractions(city, budget)
        else:
            raise ValueError("Invalid category")

        # Get closest 2 alternatives
        alternatives = get_next_closest_places(current_url, all_items, category_type=category, max_results=2)

        return {"status": "success", "data": {"alternatives": alternatives}}
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    
@app.post("/regenerate-itinerary")
def regenerate_itinerary(payload: dict):
    try:
        updated_days = []
        original_days = payload.get("original_days", [])
        replacements = payload.get("replacements", {})

        for day in original_days:
            updated_day = {
                "day": day["day"],
                "hotel": replacements.get(f"{day['day']}_hotel", day["hotel"]),
                "tours": [
                    replacements.get(f"{day['day']}_tour_{i}", t)
                    for i, t in enumerate(day["tours"])
                ],
                "attractions": [
                    replacements.get(f"{day['day']}_attraction_{i}", a)
                    for i, a in enumerate(day["attractions"])
                ],
            }
            updated_days.append(updated_day)

        final_data = payload.get("meta", {})
        final_data["days"] = updated_days

        html = run_crew_with_data(final_data)

        return {"status": "success", "data": {"itinerary_html": html}}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error regenerating itinerary")
    
    
    