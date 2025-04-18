# agents.py
import os
import json
import math
from dotenv import load_dotenv
from datetime import datetime, timedelta
from random import shuffle
from litellm import completion

load_dotenv()
os.environ["LITELLM_API_KEY"] = os.getenv("XAI_API_KEY")

# ✅ LLM config for Grok
llm_config = {
    "model": "xai/grok-2-1212",
    "provider": "grok",
    "api_key": os.getenv("XAI_API_KEY")
}

def calculate_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return float('inf')
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        R = 6371
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    except:
        return float('inf')

def find_closest_hotel(hotels, attractions):
    if not hotels or not attractions:
        return hotels[0] if hotels else None
    avg_lat = sum(float(a.get("LATITUDE", 0)) for a in attractions) / len(attractions)
    avg_lon = sum(float(a.get("LONGITUDE", 0)) for a in attractions) / len(attractions)
    return min(hotels, key=lambda h: calculate_distance(avg_lat, avg_lon, h.get("LATITUDE"), h.get("LONGITUDE")))

def run_crew_with_data(data):
    try:
        start = datetime.strptime(data["start_date"], "%Y-%m-%d")
        end = datetime.strptime(data["end_date"], "%Y-%m-%d")
        num_days = (end - start).days + 1
        date_list = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]

        hotels = data.get("hotels", [])
        tours = data.get("tours", [])[:]
        attractions = data.get("attractions", [])[:]

        shuffle(tours)
        shuffle(attractions)

        used_tours = set()
        used_attractions = set()
        days = []

        for i in range(num_days):
            today_tours = []
            today_attractions = []

            for t in tours:
                t_id = t.get("TITLE") or t.get("URL")
                if t_id not in used_tours:
                    today_tours.append(t)
                    used_tours.add(t_id)
                if len(today_tours) == 2:
                    break

            for a in attractions:
                a_id = a.get("PLACENAME") or a.get("URL")
                if a_id not in used_attractions:
                    today_attractions.append(a)
                    used_attractions.add(a_id)
                if len(today_attractions) == 2:
                    break

            hotel = find_closest_hotel(hotels, today_attractions)

            days.append({
                "day": i + 1,
                "date": date_list[i],
                "hotel": hotel,
                "tours": today_tours,
                "attractions": today_attractions
            })

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

        prompt = f'''
You are a travel itinerary expert.

Generate a professional {num_days}-day HTML travel itinerary for {data['city']} from {data['start_date']} to {data['end_date']} for {data['adults']} adults and {data['kids']} kids.

🎯 For each day include:
- 🏨 Hotel with NAME, IMAGE, ADDRESS, DISTANCE, RATING, REVIEWS, Price, CERTIFIED.
- 🚌 2 Tours with: TITLE, RATING, REVIEW COUNT, PRICE, Know More, IMAGE.
- 📍 2 Attractions with: PLACENAME, Ticket Details, HOURS, How to Reach, IMAGE, DESCRIPTION.

🖼️ Use this tag for all images:
<img src="{{IMAGE}}" alt="Item image" width="300" style="border-radius:10px; margin-bottom:10px;" />
Fallback if missing: https://placehold.co/400x300

📦 Input JSON:
{json.dumps(reduced_data, indent=2, default=str)}

📋 Output rules:
- Raw HTML only (no Markdown or backticks).
- Use <div>, <h2>, <h3>, <ul>, <p>, <img>, etc.
- Use class names like "day-card", "item-section", "image-block" for structure.
- Include one section per day, clearly labeled (Day 1, Day 2, etc).
- Add a header summary at the top with trip details.
        '''

        response = completion(
            model=llm_config["model"],
            messages=[{"role": "user", "content": prompt}],
            provider=llm_config["provider"],
            api_key=llm_config["api_key"]
        )

        html = response['choices'][0]['message']['content']
        return html, reduced_data

    except Exception as e:
        print("Grok call error:", e)
        raise RuntimeError(f"Failed to generate itinerary: {str(e)}")

def run_chat_with_agent(itinerary_text: str, question: str):
    try:
        prompt = f"""You are a helpful travel assistant. Here is the travel itinerary:\n{itinerary_text}\n\nNow answer this question based on the itinerary only:\n{question}"""

        response = completion(
            model=llm_config["model"],
            messages=[
                {"role": "system", "content": "Only answer based on the given itinerary."},
                {"role": "user", "content": prompt}
            ],
            provider=llm_config["provider"],
            api_key=llm_config["api_key"]
        )

        return response['choices'][0]['message']['content']
    except Exception as e:
        print("Chat Grok call error:", e)
        raise RuntimeError(f"Failed to get chat response: {str(e)}")
