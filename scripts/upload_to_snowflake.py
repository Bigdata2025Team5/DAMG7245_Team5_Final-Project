import boto3
import os
import pandas as pd
import snowflake.connector
from datetime import datetime
from dotenv import load_dotenv
load_dotenv(override=True)

# After geocoding is complete and CSV is saved locally
def upload_to_s3(local_file_path, bucket_name, s3_key):
    """Upload file to S3"""
    print(f"Uploading {local_file_path} to S3 bucket {bucket_name}/{s3_key}")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        s3_client.upload_file(local_file_path, bucket_name, s3_key)
        print(f"✅ Successfully uploaded to s3://{bucket_name}/{s3_key}")
        return f"s3://{bucket_name}/{s3_key}"
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        raise

def copy_from_s3_to_snowflake(s3_path, table_name="HOTEL_DATA"):
    """Copy data from S3 to Snowflake"""
    print(f"Copying data from {s3_path} to Snowflake table {table_name}")
    
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )
    
    cursor = conn.cursor()
    
    try:
        # Create external stage with AWS credentials
        cursor.execute(f"""
        CREATE OR REPLACE STAGE hotel_s3_stage
          URL = '{s3_path}'
          CREDENTIALS = (
            AWS_KEY_ID = '{os.getenv("AWS_ACCESS_KEY_ID")}'
            AWS_SECRET_KEY = '{os.getenv("AWS_SECRET_ACCESS_KEY")}'
          )
          FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = ',' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"');
        """)
        
        # Generate today's date for the data partition
        data_date = datetime.now().strftime('%Y-%m-%d')
        
        # Copy from S3 to Snowflake table
        cursor.execute(f"""
        COPY INTO {table_name} (
            CITY, NAME, LINK, IMAGE, ADDRESS, DISTANCE, RATING, REVIEWS, 
            "Price (per night)", "Room Fees", EXCLUSIONS, CERTIFIED, 
            LATITUDE, LONGITUDE, CALCULATIONMETHOD, DATA_DATE
        )
        FROM (
            SELECT 
                t.$1, t.$2, t.$3, t.$4, t.$5, t.$6, t.$7, t.$8, 
                t.$9, t.$10, t.$11, t.$12, t.$13, t.$14, t.$15,
                '{data_date}'
            FROM @hotel_s3_stage t
        )
        FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        ON_ERROR = 'CONTINUE';
        """)
        
        # Get results
        result = cursor.fetchall()
        rows_loaded = result[0][0] if result else 0
        
        print(f"✅ Successfully loaded {rows_loaded} records from S3 to Snowflake")
        return rows_loaded
        
    except Exception as e:
        print(f"❌ Error copying from S3 to Snowflake: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

# Main execution flow
def upload_geocoded_data_to_snowflake():
    """Complete pipeline to upload geocoded data via S3"""
    
    # 1. Define file paths
    geocoded_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "data", "hotels_with_coordinates.csv")
    
    # 2. Define S3 location
    bucket_name = os.getenv("AWS_S3_BUCKET")
    s3_key = f"data/hotels_with_coordinates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # 3. Upload to S3
    s3_path = upload_to_s3(geocoded_data_path, bucket_name, s3_key)
    
    # 4. Copy from S3 to Snowflake
    rows_loaded = copy_from_s3_to_snowflake(s3_path)
    
    print(f"Pipeline complete. Loaded {rows_loaded} records to Snowflake via S3.")

if __name__ == "__main__":
    upload_geocoded_data_to_snowflake()