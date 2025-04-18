import os
import sys
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Append backend path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Mock external functions before importing main
mock_fetch_hotels = MagicMock(return_value=[{"name": "Mock Hotel"}])
mock_fetch_tours = MagicMock(return_value=[{"title": "Mock Tour"}])
mock_fetch_attractions = MagicMock(return_value=[{"title": "Mock Attraction"}])
mock_run_crew = MagicMock(return_value="<html><body>Mock Itinerary</body></html>")
mock_convert_text = MagicMock(return_value="Mock Text Summary")
mock_chat = MagicMock(return_value="Mock Answer")

with patch('main.fetch_hotels', mock_fetch_hotels), \
     patch('main.fetch_tours', mock_fetch_tours), \
     patch('main.fetch_attractions', mock_fetch_attractions), \
     patch('main.run_crew_with_data', mock_run_crew), \
     patch('main.convert_itinerary_to_text', mock_convert_text), \
     patch('main.run_chat_with_agent', mock_chat):

    from main import app  # Now safely import with all dependencies mocked

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def set_env():
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["XAI_API_KEY"] = "test"
    yield

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "message": "Service is running"
    }

def test_generate_itinerary_valid():
    payload = {
        "city": "New York",
        "start_date": "2025-04-20",
        "end_date": "2025-04-22",
        "preference": "Suggest an itinerary with Things to do",
        "travel_type": "Solo",
        "adults": 1,
        "kids": 0,
        "budget": "medium",
        "include_tours": True,
        "include_accommodation": True,
        "include_things": True
    }
    response = client.post("/generate-itinerary", json=payload)
    assert response.status_code == 200
    assert "itinerary_html" in response.json()["data"]

def test_generate_itinerary_invalid_date():
    payload = {
        "city": "New York",
        "start_date": "2025-04-22",
        "end_date": "2025-04-20",  # invalid
        "preference": "Suggest an itinerary with Things to do",
        "travel_type": "Solo",
        "adults": 1,
        "kids": 0,
        "budget": "medium",
        "include_tours": True,
        "include_accommodation": True,
        "include_things": True
    }
    response = client.post("/generate-itinerary", json=payload)
    assert response.status_code == 422

def test_ask_empty_question():
    payload = {"itinerary": "Itinerary summary", "question": ""}
    response = client.post("/ask", json=payload)
    assert response.status_code in [422, 500]
