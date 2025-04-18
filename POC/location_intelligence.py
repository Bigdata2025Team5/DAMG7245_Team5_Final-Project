# location_intelligence.py
import asyncio, json
import os
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServer, MCPServerStdio
from typing import Dict, Any, List

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

async def geocode_itinerary_locations(mcp_server: MCPServer, locations: List[Dict]):
    """
    Geocode locations from an itinerary using Google Maps.
    
    Args:
        mcp_server: The MCP server instance
        locations: List of location dictionaries with at least a name/title
        
    Returns:
        List of locations with added coordinates
    """
    
    # Initialize the geocoding agent
    geocoding_agent: Agent = Agent(
        name = 'Geocoding Agent',
        instructions = """You are a mapping assistant that adds precise location data to travel itinerary points.
                          I will provide you with a list of locations (hotels, attractions, tours) from a travel itinerary.
                          
                          Your task is to:
                          1. Look up the exact coordinates for each location using Google Maps
                          2. Return the SAME list but with coordinates added to each item
                          
                          For each location, add:
                          - coordinates: {lat: number, lng: number}
                          
                          Return the enriched list in the same format it was provided, but with the coordinates added.
                          If you cannot find coordinates for a specific location, set coordinates to null.
                          
                          Use the Google Maps search tools to ensure accuracy.""",
        mcp_servers=[mcp_server],
        model = "gpt-4o-mini",
    )
    
    # Convert locations to a string representation
    locations_str = json.dumps(locations, indent=2)
    prompt = f"Please geocode these itinerary locations using Google Maps:\n\n{locations_str}"
    
    # Get the geocoded results
    result = await Runner.run(geocoding_agent, prompt)
    
    # Process the output
    if isinstance(result.final_output, str):
        # Extract JSON from the agent's output
        json_str = result.final_output
        if "```json" in json_str:
            json_str = json_str.split("```json")[1]
        if "```" in json_str:
            json_str = json_str.split("```")[0]
        
        # Parse the JSON string
        try:
            geocoded_locations = json.loads(json_str.strip())
            return geocoded_locations
        except json.JSONDecodeError as e:
            print(f"Failed to parse geocoded locations: {str(e)}")
            return locations  # Return original locations if parsing fails
    else:
        return result.final_output

async def extract_itinerary_locations(structured_data):
    """
    Extract locations from itinerary data that need to be geocoded.
    
    Args:
        structured_data: The structured itinerary data
        
    Returns:
        List of location dictionaries
    """
    locations = []
    
    # Extract hotels
    for day in structured_data.get("days", []):
        hotel = day.get("hotel")
        if hotel:
            locations.append({
                "id": f"hotel_day_{day['day']}",
                "name": hotel.get("NAME", "Unknown Hotel"),
                "address": hotel.get("ADDRESS", ""),
                "type": "hotel",
                "day": day["day"]
            })
    
    # Extract attractions
    for day in structured_data.get("days", []):
        for i, attraction in enumerate(day.get("attractions", [])):
            locations.append({
                "id": f"attraction_day_{day['day']}_{i}",
                "name": attraction.get("PLACENAME", f"Attraction {i+1}"),
                "address": attraction.get("ADDRESS", ""),
                "type": "attraction",
                "day": day["day"]
            })
    
    # Extract tours
    for day in structured_data.get("days", []):
        for i, tour in enumerate(day.get("tours", [])):
            locations.append({
                "id": f"tour_day_{day['day']}_{i}",
                "name": tour.get("TITLE", f"Tour {i+1}"),
                "address": "",  # Tours might not have specific addresses
                "type": "tour",
                "day": day["day"]
            })
    
    return locations

async def geocode_itinerary(structured_data):
    """
    Process an itinerary to add map coordinates to all locations.
    
    Args:
        structured_data: The structured itinerary data
        
    Returns:
        A dictionary with geocoded locations for the map
    """
    # Extract locations from the itinerary
    locations = await extract_itinerary_locations(structured_data)
    
    # Use Google Maps to geocode the locations
    async with MCPServerStdio(
        cache_tools_list=True,
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"], 
            "env": {"GOOGLE_MAPS_API_KEY": f"{GOOGLE_MAPS_API_KEY}"}
        },
    ) as server:
        with trace(workflow_name="Geocode Itinerary Locations"):
            geocoded_locations = await geocode_itinerary_locations(server, locations)
    
    # Organize the results by day for easy display
    result = {
        "all_locations": geocoded_locations,
        "locations_by_day": {}
    }
    
    for location in geocoded_locations:
        day = location.get("day")
        if day not in result["locations_by_day"]:
            result["locations_by_day"][day] = []
        result["locations_by_day"][day].append(location)
    
    return result