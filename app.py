# app.py
import streamlit as st
import requests
from datetime import date

# Page setup
BACKEND_URL = "http://localhost:8000"
st.set_page_config(page_title="Grok Chat", layout="wide")
st.title("✈️ Smart Travel Itinerary Generator + Chat with Grok")

# Input form
with st.form("travel_form"):
    CITIES = ["New York", "San Francisco", "Chicago", "Seattle", "Las Vegas", "Los Angeles"]
    city = st.selectbox("City", CITIES)

    start_date = st.date_input("Start Date", date.today())
    end_date = st.date_input("End Date", date.today())
    preference = st.selectbox("Preferences", [
        "Suggest an itinerary with Tours, Accommodation, Things to do",
        "Suggest an itinerary with Accommodation, Things to do",
        "Suggest an itinerary with Things to do"
    ])
    travel_type = st.radio("Travel Type", ["Solo", "With Family"])
    adults = st.number_input("Adults", min_value=1, value=1)
    kids = st.number_input("Kids", min_value=0, value=0)
    budget = st.selectbox("Budget", ["low", "medium", "high"])
    submitted = st.form_submit_button("Generate Itinerary")

# Itinerary generation
if submitted:
    with st.spinner("Generating itinerary..."):
        # Set flags based on selected preference
        include_tours = "Tours" in preference
        include_accommodation = "Accommodation" in preference
        include_things = "Things to do" in preference

        payload = {
            "city": city,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "preference": preference,
            "travel_type": travel_type,
            "adults": adults,
            "kids": kids,
            "budget": budget,
            "include_tours": include_tours,
            "include_accommodation": include_accommodation,
            "include_things": include_things
        }
        try:
            response = requests.post(f"{BACKEND_URL}/generate-itinerary", json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            itinerary_html = data["data"]["itinerary_html"]
            itinerary_text = data["data"]["itinerary_text"]

            # Store for chat use
            st.session_state.generated_itinerary = itinerary_text
            st.session_state.itinerary_html = itinerary_html
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            st.success("✅ Itinerary Generated!")

        except Exception as e:
            st.error(f"❌ Error generating itinerary: {e}")

# Always show the itinerary if it exists
if "itinerary_html" in st.session_state:
    st.components.v1.html(st.session_state.itinerary_html, height=2500, scrolling=True)

# --- Chat Interface ---
if "generated_itinerary" in st.session_state:
    st.markdown("---")
    st.subheader("💬 Ask Grok About Your Itinerary")

    question = st.text_input("❓ Your question:")
    if st.button("Ask Grok"):
        if question.strip():
            with st.spinner("Grok is thinking..."):
                try:
                    res = requests.post(
                        f"{BACKEND_URL}/ask",
                        json={"itinerary": st.session_state.generated_itinerary, "question": question},
                        timeout=60
                    )
                    res.raise_for_status()
                    answer = res.json().get("answer")
                    st.session_state.chat_history.append((question, answer))
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        else:
            st.warning("Please enter a question.")

    # Display chat history in reverse
    if st.session_state.get("chat_history"):
        st.markdown("### 🧾 Chat History")
        for q, a in st.session_state.chat_history[::-1]:
            st.markdown(f"**🧍 You:** {q}")
            st.markdown(f"**🤖 Grok:** {a}")
            st.markdown("---")
