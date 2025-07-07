# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install pip and project dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir uv \
    && uv pip install --system --no-cache-dir .

# Copy the rest of the code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 