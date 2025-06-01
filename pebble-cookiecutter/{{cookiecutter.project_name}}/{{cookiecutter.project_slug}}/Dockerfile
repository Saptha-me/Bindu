# Build stage - use slim to install dependencies
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY uv.lock /app/uv.lock
COPY pyproject.toml /app/pyproject.toml

# Install dependencies to a specific directory we'll copy later
RUN uv sync --frozen --no-install-project --system --python-path /usr/local/bin/python --target /deps

# Copy the project
COPY . /app

# Runtime stage - using distroless
FROM gcr.io/distroless/python3-debian12:latest

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages/

# Copy application code
COPY --from=builder /app /app

# Specify the command to run
CMD ["python", "{{cookiecutter.project_slug}}/app.py"]