FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy source
COPY . .

# Create runtime directories
RUN mkdir -p data/cache results logs api/static

# HF Spaces runs as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# HF Spaces requires port 7860
EXPOSE 7860

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

CMD ["python", "-m", "uvicorn", "api.server:app", \
     "--host", "0.0.0.0", "--port", "7860", \
     "--timeout-keep-alive", "120", "--workers", "1"]
