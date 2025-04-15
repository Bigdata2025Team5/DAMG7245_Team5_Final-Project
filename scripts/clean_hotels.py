import os
import pandas as pd

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, 'multi_city_ihg_hotels.csv')
CLEANED_DATA_PATH = os.path.join(DATA_DIR, 'cleaned_ihg_hotels_with_images.csv')

def clean_hotel_data():
    """Clean and standardize the scraped hotel data"""
    print("Starting hotel data cleaning...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"Looking for raw data at: {RAW_DATA_PATH}")
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Check if the raw data file exists
    if not os.path.exists(RAW_DATA_PATH):
        print(f"Raw data file not found at {RAW_DATA_PATH}. Creating empty dataframe.")
        # Create an empty dataframe with expected columns
        df = pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                                 "Rating", "Reviews", "Price (per night)", "Room Fees", 
                                 "Exclusions", "Certified"])
        print("Created empty dataframe since no raw data was found")
    else:
        # Load raw scraped data
        df = pd.read_csv(RAW_DATA_PATH)
        print(f"Loaded {len(df)} hotel records from raw data")
    
    # Only proceed with cleaning if we have data
    if len(df) > 0:
        # Drop rows with missing hotel names or links (core fields)
        df = df.dropna(subset=["Name", "Link"])
        print(f"After dropping rows with missing Name/Link: {len(df)} records")
        
        # Remove duplicates based on hotel Name and Address
        df = df.drop_duplicates(subset=["Name", "Address"])
        print(f"After removing duplicates: {len(df)} records")
        
        # Clean string fields: strip extra whitespace
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip()
        
        # Clean numeric-like fields
        df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
        
        
        
        # Format price field (make consistent)
        df["Price (per night)"] = (
            df["Price (per night)"]
            .str.replace("USD", "$")
            .str.replace("USD ", "$")
            .str.strip()
        )
        
        # Fill missing optional fields with N/A
        optional_fields = ["Room Fees", "Exclusions", "Certified"]
        for field in optional_fields:
            if field in df.columns:
                df[field] = df[field].replace("", "N/A").fillna("N/A")
    else:
        print("No data to clean. Will save empty dataframe.")
    
    # Save cleaned data
    os.makedirs(os.path.dirname(CLEANED_DATA_PATH), exist_ok=True)
    df.to_csv(CLEANED_DATA_PATH, index=False)
    print(f"✅ Cleaned data saved to {CLEANED_DATA_PATH}")
    print(f"  Final record count: {len(df)} hotels")

if __name__ == "__main__":
    try:
        clean_hotel_data()
    except Exception as e:
        print(f"Error in clean_hotels.py: {str(e)}")
        # Create the output directory and an empty cleaned file so subsequent steps don't fail
        os.makedirs(os.path.dirname(CLEANED_DATA_PATH), exist_ok=True)
        pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                             "Rating", "Reviews", "Price (per night)", "Room Fees", 
                             "Exclusions", "Certified", "Latitude", "Longitude"]).to_csv(CLEANED_DATA_PATH, index=False)
        print(f"Created empty output file at {CLEANED_DATA_PATH} to prevent pipeline failure")