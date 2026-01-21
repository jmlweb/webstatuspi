# Multi-stage build for minimal image size
# Comparable to Statping-ng (alpine-based)

# Stage 1: Build
FROM python:3.11-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Install app
COPY pyproject.toml .
COPY webstatuspi/ webstatuspi/
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime (minimal)
FROM python:3.11-alpine

WORKDIR /app

# Copy only installed packages (no pip/setuptools)
COPY --from=builder /install /usr/local

# Copy app code
COPY webstatuspi/ /app/webstatuspi/
COPY config.example.yaml /app/config.yaml

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

CMD ["python", "-m", "webstatuspi", "run", "--config", "/app/config.yaml"]
