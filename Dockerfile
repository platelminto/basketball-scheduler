FROM node:18-slim as frontend-builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy uv files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Copy built frontend assets
COPY --from=frontend-builder /app/assets/js/schedule-app/dist/ ./assets/js/schedule-app/dist/

# Collect static files
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8001

# Run migrations and start server
CMD ["sh", "-c", "uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8001"]