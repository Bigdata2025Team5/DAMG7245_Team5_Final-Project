# tests/test_main_unittest.py

import unittest
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

client = TestClient(app)


class TestFastAPIEndpoints(unittest.TestCase):

    def test_root(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "online"})

    def test_health_check(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "healthy",
            "message": "Service is running"
        })

    def test_generate_itinerary_valid(self):
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
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("itinerary_html", data)
        self.assertIn("itinerary_text", data)

    def test_generate_itinerary_invalid_dates(self):
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
        self.assertEqual(response.status_code, 422)

    def test_ask_question_empty(self):
        response = client.post("/ask", json={
            "itinerary": "Sample itinerary text.",
            "question": ""
        })
        self.assertIn(response.status_code, [422, 500])


if __name__ == "__main__":
    unittest.main()
