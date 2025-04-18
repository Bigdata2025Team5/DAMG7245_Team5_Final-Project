import streamlit as st
import requests
from datetime import date, timedelta

# Page config
st.set_page_config(page_title="✈️ AI Travel Itinerary Planner", page_icon="🌍", layout="wide")

# Constants
BACKEND_URL = "https://travel-planner-app-577642034601.us-central1.run.app"
CITIES = ["New York", "San Francisco", "Chicago", "Seattle", "Las Vegas", "Los Angeles"]
BUDGET_RANGES = ["Low (Less than $300/day)", "Medium ($300-$700/day)", "High (Above $700/day)"]

# Custom styling
st.markdown("""
    <style>
    .title { font-size: 2.5rem !important; color: #1f77b4; font-weight: 700; }
    .subtext { font-size: 1.1rem; color: #555; }
    .stButton button {
        background-color: #1f77b4; color: white; font-weight: bold;
        border-radius: 8px; padding: 10px 20px; margin-top: 10px;
    }
    .stButton button:hover { background-color: #145f90; color: #fff; }
    </style>
""", unsafe_allow_html=True)

# Session defaults
defaults = {
    "page": 1, "city": "New York",
    "start_date": date.today(),
    "end_date": date.today() + timedelta(days=3),
    "budget_range": "Medium ($300-$700/day)",
    "budget_value": "medium",
    "preference": "Suggest an itinerary with Tours, Accommodation, Things to do",
    "travel_type": "Solo",
    "adults": 1, "kids": 0,
    "itinerary_html": None
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

def format_date(d): return d.isoformat()

# --- Page 1 ---
if st.session_state.page == 1:
    st.markdown('<h1 class="title">🌍 Plan Your Dream Trip</h1>', unsafe_allow_html=True)
    st.markdown('<div class="subtext">Start by choosing your city and travel dates.</div>', unsafe_allow_html=True)
    
    st.session_state.city = st.selectbox("🗺️ Destination", CITIES)
    col1, col2 = st.columns(2)
    st.session_state.start_date = col1.date_input("📅 Start Date", st.session_state.start_date)
    st.session_state.end_date = col2.date_input("📅 End Date", st.session_state.end_date, min_value=st.session_state.start_date)

    st.session_state.budget_range = st.selectbox("💰 Budget", BUDGET_RANGES)
    if "Low" in st.session_state.budget_range:
        st.session_state.budget_value = "low"
    elif "Medium" in st.session_state.budget_range:
        st.session_state.budget_value = "medium"
    else:
        st.session_state.budget_value = "high"

    if st.button("Next ➡️"): st.session_state.page = 2; st.rerun()

# --- Page 2 ---
elif st.session_state.page == 2:
    st.markdown('<h1 class="title">🧳 Travel Preferences</h1>', unsafe_allow_html=True)
    st.session_state.preference = st.radio("🔎 What to include?", [
        "Suggest an itinerary with Tours, Accommodation, Things to do",
        "Suggest an itinerary with Accommodation, Things to do",
        "Suggest an itinerary with Things to do"
    ])
    st.session_state.travel_type = st.radio("👥 Travel Type", ["Solo", "With Family"])
    
    if st.session_state.travel_type == "With Family":
        col1, col2 = st.columns(2)
        st.session_state.adults = col1.number_input("👨 Adults", 1, 10, 2)
        st.session_state.kids = col2.number_input("🧒 Kids", 0, 10, 1)
    
    if st.button("⬅️ Back"): st.session_state.page = 1; st.rerun()
    if st.button("🎉 Generate My Itinerary"):
        st.session_state.page = 3
        st.session_state.itinerary_html = None
        st.rerun()

# --- Page 3 ---
elif st.session_state.page == 3:
    st.markdown('<h1 class="title">📋 Your AI-Powered Itinerary</h1>', unsafe_allow_html=True)
    with st.spinner("🧠 Generating itinerary..."):
        if not st.session_state.itinerary_html:
            try:
                payload = {
                    "city": st.session_state.city,
                    "start_date": format_date(st.session_state.start_date),
                    "end_date": format_date(st.session_state.end_date),
                    "preference": st.session_state.preference,
                    "travel_type": st.session_state.travel_type,
                    "adults": st.session_state.adults,
                    "kids": st.session_state.kids,
                    "budget": st.session_state.budget_value
                }
                res = requests.post(f"{BACKEND_URL}/generate-itinerary", json=payload)
                st.session_state.itinerary_html = res.json()["data"]["itinerary_html"]
            except Exception as e:
                st.error(f"❌ Error generating itinerary: {e}")
                st.stop()
    st.components.v1.html(st.session_state.itinerary_html.strip("`").replace("```html", "").replace("```", ""), height=1600, scrolling=True)

    col1, col2 = st.columns(2)
    if col1.button("🔁 Plan Another Trip"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    if col2.button("🔧 Customize Itinerary"):
        st.session_state.page = 4
        st.rerun()

# --- Page 4: Meta Prompting ---
elif st.session_state.page == 4:
    st.markdown('<h1 class="title">🔄 Replace Part of Your Itinerary</h1>', unsafe_allow_html=True)

    selected_day = st.selectbox("📅 Choose Day to Customize", [d["day"] for d in st.session_state.original_data["days"]])
    current_day = next(d for d in st.session_state.original_data["days"] if d["day"] == selected_day)

    category = st.selectbox("🔁 Category to Replace", ["accommodation", "tour", "attraction"])

    if category == "accommodation":
        options = [current_day["hotel"]["NAME"]]
        selected_item = st.selectbox("🏨 Current Hotel", options)
        current_url = current_day["hotel"].get("LINK")
    elif category == "tour":
        options = [t["TITLE"] for t in current_day["tours"]]
        selected_item = st.selectbox("🚌 Current Tour", options)
        current_url = next(t["Know More"] for t in current_day["tours"] if t["TITLE"] == selected_item)
    elif category == "attraction":
        options = [a["Title"] for a in current_day["attractions"]]
        selected_item = st.selectbox("📍 Current Attraction", options)
        current_url = next(a["URL"] for a in current_day["attractions"] if a["Title"] == selected_item)

    if st.button("🔍 Find Alternatives"):
        payload = {
            "city": st.session_state.city,
            "category": category,
            "current_url": current_url,
            "budget": st.session_state.budget
        }
        try:
            res = requests.post(f"{BACKEND_URL}/get-alternatives", json=payload)
            res.raise_for_status()
            alternatives = res.json()["data"]["alternatives"]

            if not alternatives:
                st.warning("No close alternatives found.")
            for idx, alt in enumerate(alternatives):
                st.image(alt.get("IMAGE") or alt.get("Image", "https://placehold.co/400x300"), width=300)
                st.markdown(f"**{alt.get('TITLE', alt.get('NAME'))}**")
                st.markdown(f"📍 {alt.get('ADDRESS', alt.get('Description', '--'))}")
                st.markdown(f"💰 {alt.get('PRICE', '--')} | ⭐ {alt.get('RATING', '--')}")
                if st.button(f"✅ Replace with this", key=f"alt_{idx}"):
                    key = f"{selected_day}_{category}_{current_url}"
                    st.session_state.replacements[key] = alt
                    st.success("✅ Replacement saved. Regenerating itinerary...")
                    payload = {
                        "original_data": st.session_state.original_data,
                        "replacements": st.session_state.replacements
                    }
                    regen = requests.post(f"{BACKEND_URL}/regenerate-itinerary", json=payload)
                    st.session_state.itinerary_html = regen.json()["data"]["itinerary_html"]
                    st.session_state.page = 3
                    st.rerun()
        except Exception as e:
            st.error(f"Error fetching alternatives: {e}")
