# Use a builder image to compile Python dependencies with the tools they need
# without keeping those build tools in the final runtime image.
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

# Upgrade pip tooling and build wheels for every dependency so the runtime image
# can install them without a compiler.
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip wheel --wheel-dir /tmp/wheels --requirement requirements.txt


# Final runtime image that only contains the interpreter, dependencies, and app
# source code.
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    FLASK_DEBUG=0

WORKDIR /app

COPY --from=builder /tmp/wheels /tmp/wheels
COPY requirements.txt ./requirements.txt

# Install dependencies from the wheels produced in the builder stage and clean
# up the temporary build artifacts to keep the image lean.
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-index --find-links=/tmp/wheels --requirement requirements.txt \
    && rm -rf /tmp/wheels

# Copy the application code after installing dependencies to leverage Docker
# layer caching during rebuilds.
COPY . .

EXPOSE 5000

# Default command to run the app with Gunicorn
CMD ["gunicorn", "flask_app:app", "--bind", "0.0.0.0:5000"]
