FROM python:3.9-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports for FastAPI and Streamlit
EXPOSE 8000
EXPOSE 8501

# Create a script to run both applications
RUN echo '#!/bin/bash\n\
python -m uvicorn main:app --host 0.0.0.0 --port 8000 \n\

wait\n' > /app/start.sh

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]