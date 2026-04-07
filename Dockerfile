FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT automatically
ENV PORT=8000

# Run migration then start the server
CMD ["sh", "-c", "python scripts/migrate.py && echo 'Starting uvicorn...' && python -c 'import api.main; print(\"Import OK\")' && exec python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT 2>&1"]
