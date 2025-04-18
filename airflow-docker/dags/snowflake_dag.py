# dags/my_airflow_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Add the path to import from 'pipeline'
sys.path.append(os.path.join(os.path.dirname(__file__), 'pipeline'))
from upload_to_snowflake import run_s3_to_snowflake_task

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='s3_to_snowflake_attractions_pipeline',
    default_args=default_args,
    description='Upload cleaned attractions data from S3 to Snowflake',
    schedule_interval=None,
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=['snowflake', 's3'],
) as dag:

    upload_task = PythonOperator(
        task_id='load_csv_to_snowflake',
        python_callable=run_s3_to_snowflake_task
    )

    upload_task
