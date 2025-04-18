FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only backend code (adjust if needed)
COPY backend/ .

# Expose FastAPI port
EXPOSE 8000


# Create a script to run both applications
RUN echo '#!/bin/bash\n\

python -m uvicorn main:app --host 0.0.0.0 --port 8000 \n\

wait\n' > /app/start.sh

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]