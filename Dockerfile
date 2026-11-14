# Multi-stage production container for CrowdWise
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/ backend/
COPY config/ config/
COPY models/ models/
COPY frontend/dist/ frontend/dist/

ENV PORT=5000
ENV FLASK_DEBUG=False
ENV DATA_MODE=demo

EXPOSE 5000

CMD ["python", "backend/run.py"]
