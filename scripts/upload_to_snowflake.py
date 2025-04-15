import boto3
import os
import pandas as pd
import snowflake.connector
from datetime import datetime
from dotenv import load_dotenv
load_dotenv(override=True)

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
        return bucket_name, s3_key
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        raise

def copy_from_s3_to_snowflake(bucket_name, s3_key, table_name="HOTEL_DATA"):
    """Copy data from S3 to Snowflake"""
    print(f"Copying data from s3://{bucket_name}/{s3_key} to Snowflake table {table_name}")
    
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
        # Create table if it doesn't exist
        print(f"Creating table {table_name} if it doesn't exist...")
        cursor.execute(f"""
        CREATE OR REPLACE TABLE {table_name} (
            CITY VARCHAR(100),
            NAME VARCHAR(500),
            LINK VARCHAR(500),
            IMAGE VARCHAR(1000),
            ADDRESS VARCHAR(500),
            DISTANCE VARCHAR(200),
            RATING FLOAT,
            REVIEWS VARCHAR(200),
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
        print(f"Table {table_name} is ready")
        
        # Create or replace stage pointing to the bucket
        cursor.execute(f"""
        CREATE OR REPLACE STAGE hotel_s3_stage
          URL = 's3://{bucket_name}'
          CREDENTIALS = (
            AWS_KEY_ID = '{os.getenv("AWS_ACCESS_KEY_ID")}'
            AWS_SECRET_KEY = '{os.getenv("AWS_SECRET_ACCESS_KEY")}'
          )
          FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = ',' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"');
        """)
        print(f"✅ Created S3 stage pointing to bucket {bucket_name}")

        # Generate today's date for the data partition
        data_date = datetime.now().strftime('%Y-%m-%d')
        
        copy_command = f"""
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
            FROM @hotel_s3_stage/{s3_key} t
        )
        FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        ON_ERROR = 'CONTINUE';
        """
        
        print("Executing copy command:")
        print(copy_command)
        
        cursor.execute(copy_command)

        result = cursor.fetchall()
        print(f"Copy result: {result}")
        rows_loaded = result[0][0] if result and len(result) > 0 and len(result[0]) > 0 else 0
        print(f"✅ Successfully loaded {rows_loaded} records from S3 to Snowflake")
        
        # List files in stage to verify
        cursor.execute("LIST @hotel_s3_stage")
        stage_files = cursor.fetchall()
        print(f"Files in stage: {stage_files}")
        
        return rows_loaded

    except Exception as e:
        print(f"❌ Error copying from S3 to Snowflake: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()

def upload_geocoded_data_to_snowflake():
    """Pipeline to upload geocoded hotel data to Snowflake via S3"""
    # Define paths
    geocoded_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                      "data", "hotels_with_coordinates.csv")
    
    # Ensure credentials are set
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET',
                    'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD', 'SNOWFLAKE_ACCOUNT',
                    'SNOWFLAKE_WAREHOUSE', 'SNOWFLAKE_DATABASE', 'SNOWFLAKE_SCHEMA',
                    'SNOWFLAKE_ROLE']
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Get bucket name and use fixed filename
    bucket_name = os.getenv("AWS_S3_BUCKET")
    s3_key = "data/hotel_data.csv"  # Fixed filename
    
    # Check if the file exists before uploading
    if not os.path.exists(geocoded_data_path):
        raise FileNotFoundError(f"Geocoded data file not found at {geocoded_data_path}")
    
    # Upload to S3 and then to Snowflake
    bucket_name, s3_key = upload_to_s3(geocoded_data_path, bucket_name, s3_key)
    rows_loaded = copy_from_s3_to_snowflake(bucket_name, s3_key)
    
    print(f"Pipeline complete. Loaded {rows_loaded} records to Snowflake via S3.")


if __name__ == "__main__":
    try:
        upload_geocoded_data_to_snowflake()
    except Exception as e:
        print(f"❌ Error in upload pipeline: {e}")
        import traceback
        traceback.print_exc()
