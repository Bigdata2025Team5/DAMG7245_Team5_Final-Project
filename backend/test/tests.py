import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from io import BytesIO

# Append backend path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mocks for all external functions
mock_fetch_hotels = MagicMock(return_value=[{"name": "Mock Hotel"}])
mock_fetch_tours = MagicMock(return_value=[{"title": "Mock Tour"}])
mock_fetch_attractions = MagicMock(return_value=[{"title": "Mock Attraction"}])
mock_fetch_hidden_gems = MagicMock(return_value=[{"name": "Hidden Gem"}])
mock_run_crew = MagicMock(return_value="<html><body>Mock Itinerary</body></html>")
mock_convert_text = MagicMock(return_value="Mock Text Summary")
mock_chat = MagicMock(return_value="Mock Answer")
mock_pdf = MagicMock(return_value=BytesIO(b"%PDF-1.4\n%Mock PDF"))

# Apply all mocks before importing app
with patch('agents.run_crew_with_data', mock_run_crew), \
     patch('snowflake_fetch.fetch_hotels', mock_fetch_hotels), \
     patch('snowflake_fetch.fetch_tours', mock_fetch_tours), \
     patch('snowflake_fetch.fetch_attractions', mock_fetch_attractions), \
     patch('pinecone_fetch.fetch_hidden_gems', mock_fetch_hidden_gems), \
     patch('llm_formating.convert_itinerary_to_text', mock_convert_text), \
     patch('agents.run_chat_with_agent', mock_chat), \
     patch('generate_pdf.create_itinerary_pdf', mock_pdf):
    
    from main import app

client = TestClient(app)

# Set dummy environment variables
@pytest.fixture(scope="module", autouse=True)
def set_env():
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["XAI_API_KEY"] = "test"
    yield

# ---------------- Test Cases ---------------- #

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online"}

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
    data = response.json()["data"]
    assert "itinerary_html" in data
    assert "itinerary_text" in data

def test_generate_itinerary_invalid_date():
    payload = {
        "city": "New York",
        "start_date": "2025-04-22",
        "end_date": "2025-04-20",  # End date before start
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
    response = client.post("/ask", json={"itinerary": "Mock itinerary", "question": ""})
    assert response.status_code == 200
    assert response.json() == {"answer": "Mock Answer"}


def test_generate_pdf_success():
    payload = {
        "city": "New York",
        "itinerary": "Mock itinerary for PDF",
        "start_date": "2025-04-20"
    }
    response = client.post("/generate-pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
