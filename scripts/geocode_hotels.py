import os
import csv
import math
import random
import pandas as pd

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CLEANED_DATA_PATH = os.path.join(DATA_DIR, 'cleaned_ihg_hotels_with_images.csv')
GEOCODED_DATA_PATH = os.path.join(DATA_DIR, 'hotels_with_coordinates.csv')

# Define city center coordinates for geocoding
CITY_CENTERS = {
    'New York': {'lat': 40.7128, 'lng': -73.9856},
    'Chicago': {'lat': 41.8781, 'lng': -87.6298},
    'San Francisco': {'lat': 37.7749, 'lng': -122.4194},
    'Seattle': {'lat': 47.6062, 'lng': -122.3321},
    'Las Vegas': {'lat': 36.1699, 'lng': -115.1398},
    'Los Angeles': {'lat': 34.0522, 'lng': -118.2437}
}

def parse_distance(distance_str):
    """
    Extract distance in kilometers from the Distance column
    Example: "0.17 mi (0.28 km) from city center" -> 0.28
    """
    try:
        # Extract the part in parentheses containing kilometers
        km_part = distance_str.split('(')[1].split(')')[0]
        # Extract the number
        km = float(km_part.split(' ')[0])
        return km
    except (IndexError, ValueError):
        print(f"  Could not parse distance: {distance_str}")
        return None

def calculate_coordinates(city_center, distance_km, angle=None):
    """
    Calculate coordinates at a given distance from city center
    Uses a random angle if none is provided
    """
    # Earth's radius in kilometers
    EARTH_RADIUS = 6371.0
    
    # Convert coordinates to radians
    lat1 = math.radians(city_center['lat'])
    lon1 = math.radians(city_center['lng'])
    
    # Use random angle if none provided
    if angle is None:
        angle = random.uniform(0, 360)
    
    # Convert angle to radians
    bearing = math.radians(angle)
    
    # Calculate new position
    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance_km / EARTH_RADIUS) +
        math.cos(lat1) * math.sin(distance_km / EARTH_RADIUS) * math.cos(bearing)
    )
    
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(distance_km / EARTH_RADIUS) * math.cos(lat1),
        math.cos(distance_km / EARTH_RADIUS) - math.sin(lat1) * math.sin(lat2)
    )
    
    # Convert back to degrees
    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)
    
    return {'lat': lat2, 'lng': lon2}

def geocode_hotels():
    """Add geographical coordinates to hotel data"""
    print("Starting hotel geocoding process...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Looking for cleaned data at: {CLEANED_DATA_PATH}")
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Check if the cleaned data file exists
    if not os.path.exists(CLEANED_DATA_PATH):
        print(f"Cleaned data file not found at {CLEANED_DATA_PATH}. Creating empty dataframe.")
        # Create an empty file with expected columns
        default_columns = ["City", "Name", "Link", "Image", "Address", "Distance", 
                         "Rating", "Reviews", "Price (per night)", "Room Fees", 
                         "Exclusions", "Certified"]
        fieldnames = default_columns + ['Latitude', 'Longitude', 'CalculationMethod']
        
        # Create empty DataFrame and save it to geocoded path
        df = pd.DataFrame(columns=fieldnames)
        os.makedirs(os.path.dirname(GEOCODED_DATA_PATH), exist_ok=True)
        df.to_csv(GEOCODED_DATA_PATH, index=False)
        print(f"Created empty geocoded file at {GEOCODED_DATA_PATH}")
        return
    
    try:
        # Read input CSV
        with open(CLEANED_DATA_PATH, 'r', encoding='utf-8', errors='replace') as input_file:
            reader = csv.DictReader(input_file)
            all_rows = list(reader)
        
        total_rows = len(all_rows)
        print(f"Total hotels to process: {total_rows}")
        
        # If no rows, create an empty output file with expected columns
        if total_rows == 0:
            print("No hotels to process. Creating empty output file.")
            # Get default columns from the CSV header or use a default set
            try:
                with open(CLEANED_DATA_PATH, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.reader(f)
                    header = next(reader, [])
                    if not header:
                        header = ["City", "Name", "Link", "Image", "Address", "Distance", 
                                 "Rating", "Reviews", "Price (per night)", "Room Fees", 
                                 "Exclusions", "Certified"]
            except:
                header = ["City", "Name", "Link", "Image", "Address", "Distance", 
                         "Rating", "Reviews", "Price (per night)", "Room Fees", 
                         "Exclusions", "Certified"]
            
            fieldnames = header + ['Latitude', 'Longitude', 'CalculationMethod']
            
            # Create an empty output file
            os.makedirs(os.path.dirname(GEOCODED_DATA_PATH), exist_ok=True)
            with open(GEOCODED_DATA_PATH, 'w', encoding='utf-8', newline='') as output_file:
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
            
            print(f"✅ Empty geocoded data file created at {GEOCODED_DATA_PATH}")
            return
        
        # Define fieldnames with new columns
        fieldnames = list(all_rows[0].keys()) + ['Latitude', 'Longitude', 'CalculationMethod']
        
        # Process the CSV
        results = []
        for idx, row in enumerate(all_rows):
            hotel_name = row.get('Name', '').strip()
            city = row.get('City', '').strip()
            distance_str = row.get('Distance', '').strip()
            
            if (idx + 1) % 20 == 0 or idx == 0:
                print(f"Processing hotel {idx+1}/{total_rows}: {hotel_name}")
            
            # Check if we have city center coordinates
            if city in CITY_CENTERS:
                city_center = CITY_CENTERS[city]
                
                # Parse distance
                distance_km = parse_distance(distance_str)
                
                if distance_km is not None:
                    # Determine angle (we'll use hotel name to generate a consistent angle)
                    # This ensures the same hotel always gets the same coordinates
                    name_hash = sum(ord(c) for c in hotel_name)
                    angle = (name_hash % 360)
                    
                    # Calculate coordinates
                    coords = calculate_coordinates(city_center, distance_km, angle)
                    
                    # Add coordinates to the row
                    updated_row = row.copy()
                    updated_row['Latitude'] = coords['lat']
                    updated_row['Longitude'] = coords['lng']
                    updated_row['CalculationMethod'] = f"Distance-based ({distance_km} km from city center, angle {angle}°)"
                else:
                    # Couldn't parse distance, use city center
                    updated_row = row.copy()
                    updated_row['Latitude'] = city_center['lat']
                    updated_row['Longitude'] = city_center['lng']
                    updated_row['CalculationMethod'] = "City center (couldn't parse distance)"
            else:
                # Unknown city, leave coordinates blank
                updated_row = row.copy()
                updated_row['Latitude'] = ''
                updated_row['Longitude'] = ''
                updated_row['CalculationMethod'] = "Unknown city"
            
            results.append(updated_row)
        
        # Write results to output CSV
        os.makedirs(os.path.dirname(GEOCODED_DATA_PATH), exist_ok=True)
        with open(GEOCODED_DATA_PATH, 'w', encoding='utf-8', newline='') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Geocoded data saved to {GEOCODED_DATA_PATH}")
        print(f"  Total records processed: {len(results)}")
        
    except Exception as e:
        print(f"Error processing CSV: {e}")
        # Create an empty output file to prevent pipeline failure
        default_columns = ["City", "Name", "Link", "Image", "Address", "Distance", 
                         "Rating", "Reviews", "Price (per night)", "Room Fees", 
                         "Exclusions", "Certified", "Latitude", "Longitude", "CalculationMethod"]
        
        os.makedirs(os.path.dirname(GEOCODED_DATA_PATH), exist_ok=True)
        pd.DataFrame(columns=default_columns).to_csv(GEOCODED_DATA_PATH, index=False)
        print(f"Created empty output file at {GEOCODED_DATA_PATH} to prevent pipeline failure")
        raise

if __name__ == "__main__":
    try:
        geocode_hotels()
    except Exception as e:
        print(f"Unhandled error in geocode_hotels.py: {e}")
        # Final fallback to ensure an output file exists
        default_columns = ["City", "Name", "Link", "Image", "Address", "Distance", 
                         "Rating", "Reviews", "Price (per night)", "Room Fees", 
                         "Exclusions", "Certified", "Latitude", "Longitude", "CalculationMethod"]
        
        os.makedirs(os.path.dirname(GEOCODED_DATA_PATH), exist_ok=True)
        pd.DataFrame(columns=default_columns).to_csv(GEOCODED_DATA_PATH, index=False)
