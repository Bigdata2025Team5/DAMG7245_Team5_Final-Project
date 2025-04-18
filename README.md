# DAMG7245_Team5_Final-Project

## Project Overview

This project builds an intelligent end to end system that focuses on automating the creation of personalized travel itineraries using LLM and big data. It combines structured data – hotels, attractions in the cities and various day tours available in cities, with unstructured content from youtube video transcripts to create full-fledged travel plans. The project provides options to users to input their preferences like travel destination, dates, and interests. Once the options are provided the system creates day wise itineraries based on individual travel style.

The unique characteristic of the system is the orchestration of various technologies working together. Apache Airflow handles automated data ingestion into Snowflake to store structured data, and into Pinecone to store unstructured embeddings. LLM is paired with different CrewAI agents which helps in the itinerary generation logic. The frontend of the system is developed using Streamlit for a smooth user experience and FastAPI for the backend communication. The entire data pipeline is designed with the focus on scalability and real world usability, so the system is both technically sound and actually helpful to a wide range of users.

---

## Links 
Codelabs : https://codelabs-preview.appspot.com/?file_id=1Ivaei3z5WiFeuO5PGgW__qULga5uAJL4WloMry3UyXQ#0

Streamlit: https://team5finalproject-ea3y3tk52ebfva8kgb7rxb.streamlit.app/ 

FastApi: https://travel-planner-app-577642034601.us-central1.run.app/docs

Airflow: http://34.132.144.105:8080/home

---

## Technologies Used

[![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![Apache Airflow](https://img.shields.io/badge/Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)](https://airflow.apache.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-000000?style=for-the-badge&logo=data:image/svg+xml;base64,YOUR_BASE64_ENCODED_LOGO&logoColor=white)](https://www.crewai.com/)
[![Amazon AWS](https://img.shields.io/badge/Amazon_AWS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![Snowflake](https://img.shields.io/badge/Snowflake-00A9E0?style=for-the-badge&logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![Docker](https://img.shields.io/badge/Docker-%232496ED?style=for-the-badge&logo=Docker&color=blue&logoColor=white)](https://www.docker.com)
[![Google Cloud](https://img.shields.io/badge/Google_Cloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)](https://cloud.google.com)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/)

---

## Architecture Diagram

![AI-Generated Travel Itinerary](https://github.com/Bigdata2025Team5/DAMG7245_Team5_Final-Project/blob/main/Diagrams/ai_travel_itinerary_system_architecture.png)

---

## How to Run Application Locally

### Prerequisites
- Python 3.8+
- Snowflake, and AWS S3 account and credentials
- API keys for OpenAI, Pinecone, YouTube API

### Setup Instructions

1. **Clone the repository using git clone**
   
3. **Install dependencies**:   
   ```
   pip install -r requirements.txt
   ```
4. **Configure the environment variables in .env**
   
5. **Run the FastAPI server**:
   ```
   uvicorn app:app --reload
   ```
   
6. **Run the Streamlit app**:
   ```
   streamlit run streamlit_app.py
   ```
   
---

## 📂 Project Structure
```
├── Backend
│   └── Dockerfile
|   ├── main.py
|   ├── requirements.txt
├── Frontend
│   ├── app.py
│   ├── requirements.txt
├── airflow-docker
│   └── Dockerfile
|   ├── docker-compose.yaml
|   ├── requirements.txt
|   ├── dags
|       └── hotel_scrape_dag.py
|       └── youtube_dag.py
|       └── Dockerfile
├── Diagrams
│   ├── ai_travel_itinerary_system_architecture.png
├── Documentation
├── POC  
├── AiDisclosure.md
├── README.md

```


---

## Team Information
| Name            | Student ID    | Contribution |
|----------------|--------------|--------------|
| **Pranjal Mahajan** | 002375449  | 33.33% |
| **Srushti Patil**  | 002345025  | 33.33% |
| **Ram Putcha**  | 002304724  | 33.33% |

---
