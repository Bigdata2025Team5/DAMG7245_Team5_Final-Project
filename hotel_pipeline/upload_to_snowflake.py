import os
import csv
import pandas as pd
import snowflake.connector
from datetime import datetime
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv
load_dotenv(override=True)
# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
GEOCODED_DATA_PATH = os.path.join(DATA_DIR, 'hotels_with_coordinates.csv')

def get_snowflake_connection():
    """Create a connection to Snowflake using environment variables"""
    try:
        return snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA")
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
    
    # Check if the geocoded data file exists
    if not os.path.exists(GEOCODED_DATA_PATH):
        raise FileNotFoundError(f"Geocoded data file not found at {GEOCODED_DATA_PATH}")
    
    # Load the data
    df = pd.read_csv(GEOCODED_DATA_PATH)
    print(f"Loaded {len(df)} records from geocoded data")
    
    # Generate today's date for the data partition
    data_date = datetime.now().strftime('%Y-%m-%d')
    
    # Convert empty strings to None for Snowflake compatibility
    df = df.replace('', None)
    
    # Create a temporary file for the data
    with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
        df.to_csv(temp_file.name, index=False, quoting=csv.QUOTE_NONNUMERIC)
        temp_file_path = temp_file.name
    
    print(f"Temporary file created at {temp_file_path}")
    
    try:
        # Connect to Snowflake
        conn = get_snowflake_connection()
        print("Connected to Snowflake")
        
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
        staged_file_name = staged_files_res[0][0].split('/')[1] if staged_files_res else None
        
        if not staged_file_name:
            raise Exception("Failed to stage the file in Snowflake")
        
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
        raise
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"Removed temporary file: {temp_file_path}")

if __name__ == "__main__":
    upload_to_snowflake()