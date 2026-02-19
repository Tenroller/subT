# ──────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder - Install dependencies and create virtual environment
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Install build dependencies (git needed for some Python packages)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv --seed /app/.venv && \
    . /app/.venv/bin/activate && \
    uv sync --frozen --no-dev

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime - Minimal production image
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY main.py transcriber.py subtitle_generator.py video_processor.py translator.py ./

# Create directories for uploads and outputs
RUN mkdir -p uploads outputs

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose the backend port
EXPOSE 4569

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4569"]
