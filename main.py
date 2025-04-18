# main.py
import os
import json
import traceback
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from datetime import date
from typing import Literal
from dotenv import load_dotenv
from agents import run_crew_with_data, run_chat_with_agent
from snowflake_fetch import (
    fetch_attractions,
    fetch_hotels,
    fetch_tours,
    convert_decimal_to_float,
    get_next_closest_places
)
from llm_formating import convert_itinerary_to_text

load_dotenv(override=True)
os.environ["LITELLM_API_KEY"] = os.getenv("XAI_API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ----------------- Models -----------------

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
    include_tours: bool = True
    include_accommodation: bool = True
    include_things: bool = True

    @field_validator('end_date')
    def end_date_after_start(cls, end_date, values):
        if 'start_date' in values.data and end_date < values.data['start_date']:
            raise ValueError("End date must be after start date")
        return end_date

class ChatRequest(BaseModel):
    itinerary: str
    question: str

# ----------------- Helpers -----------------

def fetch_itinerary_data(city, start_date, end_date, travel_type, adults, kids, budget,
                         include_tours=True, include_accommodation=True, include_things=True):
    print("--- FETCHING ITINERARY DATA ---")
    print(f"City: {city}, Budget: {budget}, Start: {start_date}, End: {end_date}")
    print(f"Include Tours: {include_tours}, Include Accommodations: {include_accommodation}, Include Things to Do: {include_things}")
    hotels = convert_decimal_to_float(fetch_hotels(city, budget)) if include_accommodation else []
    print(f"Fetched {len(hotels)} hotels")
    tours = convert_decimal_to_float(fetch_tours(city, budget)) if include_tours else []
    print(f"Fetched {len(tours)} tours")
    attractions = convert_decimal_to_float(fetch_attractions(city, budget, include_free=True)) if include_things else []
    print(f"Fetched {len(attractions)} attractions")

    return {
        "city": city,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "travel_type": travel_type,
        "adults": adults,
        "kids": kids,
        "budget": budget,
        "hotels": hotels,
        "tours": tours,
        "attractions": attractions
    }

# ----------------- Routes -----------------

@app.get("/")
def root():
    return {"status": "online"}

@app.post("/generate-itinerary")
def generate_itinerary(payload: ItineraryInput):
    try:
        structured_data = fetch_itinerary_data(
            city=payload.city,
            start_date=payload.start_date,
            end_date=payload.end_date,
            travel_type=payload.travel_type,
            adults=payload.adults,
            kids=payload.kids,
            budget=payload.budget,
            include_tours=payload.include_tours,
            include_accommodation=payload.include_accommodation,
            include_things=payload.include_things
        )

        html = run_crew_with_data(structured_data)
        text_summary = convert_itinerary_to_text(html)

        return {
            "status": "success",
            "data": {
                "itinerary_html": html,
                "itinerary_text": text_summary
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

        if category == "hotel":
            all_items = fetch_hotels(city, budget)
        elif category == "tour":
            all_items = fetch_tours(city, budget)
        elif category == "attraction":
            all_items = fetch_attractions(city, budget)
        else:
            raise ValueError("Invalid category")

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
        text_summary = convert_itinerary_to_text(html)

        return {"status": "success", "data": {
            "itinerary_html": html,
            "itinerary_text": text_summary
        }}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error regenerating itinerary")

@app.post("/ask")
def ask_question(req: ChatRequest):
    try:
        answer = run_chat_with_agent(req.itinerary, req.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Main Entry -----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
