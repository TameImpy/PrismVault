FROM python:3.11-slim

# Cache bust: 2026-04-07-v2
ENV BUILD_VERSION=2

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT automatically
ENV PORT=8000

# Run migration then start the server
CMD ["python", "start.py"]
