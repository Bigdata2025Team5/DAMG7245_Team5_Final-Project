# tests/test_main.py

import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app


client = TestClient(app)


@pytest.mark.unit
def test_root():
    """Unit: Root status endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online"}


@pytest.mark.unit
def test_health_check():
    """Unit: Health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "message": "Service is running"
    }


@pytest.mark.integration
def test_generate_itinerary_valid():
    """Integration: Valid itinerary generation"""
    payload = {
        "city": "New York",
        "start_date": "2025-04-20",
        "end_date": "2025-04-22",
        "preference": "Suggest an itinerary with Things to do",
        "travel_type": "Solo",
        "adults": 1,
        "kids": 0,
        "budget": "medium",
        "include_tours": False,
        "include_accommodation": False,
        "include_things": True
    }
    response = client.post("/generate-itinerary", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "itinerary_html" in data
    assert "itinerary_text" in data


@pytest.mark.integration
def test_generate_itinerary_invalid_dates():
    """Integration: Itinerary generation fails if end_date < start_date"""
    payload = {
        "city": "Chicago",
        "start_date": "2025-04-25",
        "end_date": "2025-04-20",
        "preference": "Suggest an itinerary with Things to do",
        "travel_type": "Solo",
        "adults": 1,
        "kids": 0,
        "budget": "medium",
        "include_tours": False,
        "include_accommodation": False,
        "include_things": True
    }
    response = client.post("/generate-itinerary", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
def test_ask_question_empty():
    """Integration: Ask endpoint fails with empty question"""
    response = client.post("/ask", json={
        "itinerary": "Sample itinerary text.",
        "question": ""
    })
    assert response.status_code in [422, 500]
