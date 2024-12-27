FROM python:3.10.15-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ /app/src/
COPY migrations/ /app/migrations/

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:7071", "--workers", "4", "--threads", "2", "src.app:create_app()"]