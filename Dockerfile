FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Railway injects PORT automatically; default to 8080 for local testing
EXPOSE 8080

# Use exec form so uvicorn receives SIGTERM for graceful shutdown
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
