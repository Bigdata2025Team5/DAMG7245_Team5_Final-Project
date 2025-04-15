import os
import csv
import pandas as pd
import snowflake.connector
from datetime import datetime
from tempfile import NamedTemporaryFile

# Try to load from .env file for local development, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print("Loaded environment from .env file")
except ImportError:
    print("dotenv package not available, using environment variables directly")

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
GEOCODED_DATA_PATH = os.path.join(DATA_DIR, 'hotels_with_coordinates.csv')

def get_snowflake_connection():
    """Create a connection to Snowflake using environment variables"""
    try:
        print("Connecting to Snowflake...")
        print(f"Account: {os.getenv('SNOWFLAKE_ACCOUNT')}")
        print(f"User: {os.getenv('SNOWFLAKE_USER')}")
        print(f"Database: {os.getenv('SNOWFLAKE_DATABASE')}")
        print(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
        print(f"Warehouse: {os.getenv('SNOWFLAKE_WAREHOUSE')}")
        
        return snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE")
        )
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        raise

def create_stage_if_not_exists(conn):
    """Create a stage in Snowflake if it doesn't exist"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE STAGE IF NOT EXISTS HOTEL_DATA_STAGE
          FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = ',' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        """)
        print("✅ Snowflake stage HOTEL_DATA_STAGE is ready")
    finally:
        cursor.close()

def create_table_if_not_exists(conn):
    """Create the hotel data table in Snowflake if it doesn't exist"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS HOTEL_DATA (
            CITY VARCHAR(100),
            NAME VARCHAR(500),
            LINK VARCHAR(500),
            IMAGE VARCHAR(1000),
            ADDRESS VARCHAR(500),
            DISTANCE VARCHAR(200),
            RATING FLOAT,
            REVIEWS INTEGER,
            "Price (per night)" VARCHAR(100),
            "Room Fees" VARCHAR(500),
            EXCLUSIONS VARCHAR(500),
            CERTIFIED VARCHAR(200),
            LATITUDE FLOAT,
            LONGITUDE FLOAT,
            CALCULATIONMETHOD VARCHAR(200),
            DATA_DATE DATE
        )
        """)
        print("✅ Snowflake table HOTEL_DATA is ready")
    finally:
        cursor.close()

def upload_to_snowflake():
    """Upload hotel data to Snowflake"""
    print("Starting upload to Snowflake...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Looking for geocoded data at: {GEOCODED_DATA_PATH}")
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Check if the geocoded data file exists
    if not os.path.exists(GEOCODED_DATA_PATH):
        print(f"Warning: Geocoded data file not found at {GEOCODED_DATA_PATH}. Creating an empty dataframe.")
        # Create empty dataframe with expected columns
        df = pd.DataFrame(columns=["City", "Name", "Link", "Image", "Address", "Distance", 
                                 "Rating", "Reviews", "Price (per night)", "Room Fees", 
                                 "Exclusions", "Certified", "Latitude", "Longitude", "CalculationMethod"])
    else:
        # Load the data
        df = pd.read_csv(GEOCODED_DATA_PATH)
        print(f"Loaded {len(df)} records from geocoded data")
    
    # Generate today's date for the data partition
    data_date = datetime.now().strftime('%Y-%m-%d')
    
    # Convert empty strings to None for Snowflake compatibility
    df = df.replace('', None)
    
    # If dataframe is empty, create a sample row to ensure schema compatibility
    if len(df) == 0:
        print("Creating sample row for empty dataframe...")
        df = pd.DataFrame([{
            "City": "Sample", 
            "Name": "Sample Hotel", 
            "Link": "https://example.com", 
            "Image": "https://example.com/image.jpg",
            "Address": "123 Sample St", 
            "Distance": "0.0 mi (0.0 km) from city center", 
            "Rating": 0.0, 
            "Reviews": 0, 
            "Price (per night)": "$0", 
            "Room Fees": "N/A", 
            "Exclusions": "N/A", 
            "Certified": "N/A",
            "Latitude": 0.0,
            "Longitude": 0.0,
            "CalculationMethod": "Sample"
        }])
        print("Added sample row for schema compatibility")
    
    # Create a temporary file for the data
    temp_file_path = None
    try:
        with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            df.to_csv(temp_file.name, index=False, quoting=csv.QUOTE_NONNUMERIC)
            temp_file_path = temp_file.name
        
        print(f"Temporary file created at {temp_file_path}")
        
        # Check environment variables
        required_env_vars = ["SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_ACCOUNT", 
                           "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Connect to Snowflake
        conn = get_snowflake_connection()
        print("Connected to Snowflake successfully")
        
        # Ensure stage and table exist
        create_stage_if_not_exists(conn)
        create_table_if_not_exists(conn)
        
        # Upload file to stage
        cursor = conn.cursor()
        put_command = f"PUT file://{temp_file_path} @HOTEL_DATA_STAGE/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
        print(f"Executing: {put_command}")
        cursor.execute(put_command)
        
        # Get the staged file name
        staged_files_res = cursor.fetchall()
        print(f"Stage result: {staged_files_res}")
        
        if not staged_files_res:
            raise Exception("Failed to stage the file in Snowflake (no results returned)")
        
        staged_file_name = staged_files_res[0][0].split('/')[-1]
        print(f"File staged as: {staged_file_name}")
        
        # Copy data from stage to table
        copy_command = f"""
        COPY INTO HOTEL_DATA (
            CITY, NAME, LINK, IMAGE, ADDRESS, DISTANCE, RATING, REVIEWS, 
            "Price (per night)", "Room Fees", EXCLUSIONS, CERTIFIED, 
            LATITUDE, LONGITUDE, CALCULATIONMETHOD, DATA_DATE
        )
        FROM (
            SELECT 
                t.$1, t.$2, t.$3, t.$4, t.$5, t.$6, t.$7, t.$8, 
                t.$9, t.$10, t.$11, t.$12, t.$13, t.$14, t.$15, 
                '{data_date}'
            FROM @HOTEL_DATA_STAGE/{staged_file_name} t
        )
        FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        ON_ERROR = 'CONTINUE'
        """
        
        print("Copying data from stage to Snowflake table...")
        cursor.execute(copy_command)
        
        # Get the results
        result = cursor.fetchall()
        rows_loaded = result[0][0] if result else 0
        
        print(f"✅ Successfully loaded {rows_loaded} records to Snowflake with data_date: {data_date}")
        
        # Clean up the stage
        cursor.execute(f"REMOVE @HOTEL_DATA_STAGE/{staged_file_name}")
        print("Cleaned up staged file")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error uploading to Snowflake: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"Removed temporary file: {temp_file_path}")

if __name__ == "__main__":
    try:
        upload_to_snowflake()
    except Exception as e:
        print(f"Unhandled error in upload_to_snowflake.py: {e}")
        import traceback
        traceback.print_exc()
