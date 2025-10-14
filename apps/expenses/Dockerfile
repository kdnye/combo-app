# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY fsi_expenses_web ./fsi_expenses_web
RUN pip install --upgrade pip \
    && pip install .

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=fsi_expenses_web:create_app
WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app
RUN pip install --no-cache-dir gunicorn && mkdir -p /app/instance/uploads
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "fsi_expenses_web:create_app()"]
