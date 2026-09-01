# Dockerfile
FROM python:3.11-slim

# Install system dependencies (libpq for psycopg2, tk for the Tk GUI)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# uv binary, via the official multi-stage distribution image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# tkinter only exists in the system python's stdlib (via python3-tk above),
# so point uv at it instead of letting it download its own interpreter build.
ENV UV_PYTHON_PREFERENCE=only-system \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install Python dependencies first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the application and install it
COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["python", "-m", "dicom_connector.main"]
