from diagrams import Diagram, Cluster
from diagrams.aws.storage import S3
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.client import Users
from diagrams.custom import Custom

with Diagram("AI Travel Itinerary System Architecture", show=True, direction="LR"):

    # User and Frontend
    user = Users("User (Streamlit UI)")
    streamlit = Custom("Streamlit App", "icons/streamlit.png")

    # Backend Layer
    with Cluster("Backend/API Layer"):
        fastapi = Custom("FastAPI", "icons/fastapi.png")  # Placeholder, or use a Python icon
        crewai = Custom("CrewAI Agents", "icons/crewai.png")
        llm = Custom("LLM (GPT-4o)", "icons/grok.png")

    # Storage
    with Cluster("Storage Layer"):
        s3 = S3("AWS S3")
        snowflake = Custom("Snowflake", "icons/snowflake.png")
        pinecone = Custom("Pinecone", "icons/pinecone.png")

    # ETL Layer
    with Cluster("ETL Pipelines (Airflow)"):
        airflow1 = Airflow("IHG Hotels Pipeline")
        airflow2 = Airflow("Triphobo Pipeline")
        airflow3 = Airflow("YouTube Transcript Pipeline")

    # External Data Sources
    youtube = Custom("YouTube", "icons/youtube.png")
    triphobo = Custom("Triphobo", "icons/triphobo.png")
    ihg = Custom("IHG Hotels", "icons/ihg.png")

    # User Input Flow
    user >> streamlit >> fastapi >> crewai >> llm

    # LLM Response Flow
    llm >> fastapi >> streamlit >> user

   

    # Data Sources to ETL Pipelines
    youtube >> airflow3
    triphobo >> airflow2
    ihg >> airflow1

    # Pipelines to AWS S3
    airflow1 >> s3
    airflow2 >> s3
    airflow3 >> s3

    # S3 to Data Stores
    s3 >> snowflake
    s3 >> pinecone

    # Data Stores to LLM
    snowflake >> llm
    pinecone >> llm
