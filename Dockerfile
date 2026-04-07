FROM python:3.11-slim

# Cache bust: 2026-04-07-v2
ENV BUILD_VERSION=2

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT at runtime — don't override it here
# Default only used if PORT is not set (local Docker testing)
# ENV PORT=8000

# Run migration then start the server
EXPOSE 8000
CMD ["sh", "start.sh"]
