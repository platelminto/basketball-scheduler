FROM node:18-slim as frontend-builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM debian:bookworm-slim

WORKDIR /app

# Build-time arguments from Coolify
ARG DEBUG
ARG SECRET_KEY
ARG DATABASE_URL
ARG ALLOWED_HOSTS

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

# Make build args available as env vars for Django commands
ENV DEBUG=${DEBUG}
ENV SECRET_KEY=${SECRET_KEY}
ENV DATABASE_URL=${DATABASE_URL}
ENV ALLOWED_HOSTS=${ALLOWED_HOSTS}

# Collect static files
RUN uv run --no-sync python manage.py collectstatic --noinput

# Add gunicorn
RUN uv add gunicorn

EXPOSE 8000

# Run with gunicorn
CMD ["uv", "run", "--no-sync", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "league_manager.wsgi:application"]