FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (no venv, install to system)
RUN uv sync --frozen --no-dev --no-editable

# Copy application code
COPY main.py transcriber.py subtitle_generator.py video_processor.py translator.py ./

# Create directories for uploads and outputs
RUN mkdir -p uploads outputs

# Expose the backend port
EXPOSE 4569

# Run the application using uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4569"]
