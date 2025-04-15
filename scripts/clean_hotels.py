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
    
    # Check if the raw data file exists
    if not os.path.exists(RAW_DATA_PATH):
        raise FileNotFoundError(f"Raw data file not found at {RAW_DATA_PATH}")
    
    # Load raw scraped data
    df = pd.read_csv(RAW_DATA_PATH)
    print(f"Loaded {len(df)} hotel records from raw data")
    
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
    
    # Clean and standardize review count
    df["Reviews"] = (
        df["Reviews"]
        .str.replace(" reviews", "", case=False)
        .str.replace(",", "")
        .astype(str)
    )
    df["Reviews"] = pd.to_numeric(df["Reviews"], errors="coerce")
    
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
    
    # Save cleaned data
    os.makedirs(os.path.dirname(CLEANED_DATA_PATH), exist_ok=True)
    df.to_csv(CLEANED_DATA_PATH, index=False)
    print(f"✅ Cleaned data saved to {CLEANED_DATA_PATH}")
    print(f"  Final record count: {len(df)} hotels")

if __name__ == "__main__":
    clean_hotel_data()