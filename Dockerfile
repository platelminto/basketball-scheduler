FROM node:18-slim as frontend-builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM debian:bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy uv files
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev group since we don't have one)
RUN rm -rf .venv && uv sync --frozen

# Copy application code
COPY . .

# Copy built frontend assets
COPY --from=frontend-builder /app/static/bundles/ ./static/bundles/
# Copy webpack stats file
COPY --from=frontend-builder /app/webpack-stats.json ./webpack-stats.json
# Environment variables will be provided at runtime by docker-compose

# Add gunicorn
RUN uv add gunicorn

EXPOSE 8001

# Command will be specified in docker-compose.yml