FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv \
    && uv pip install -r pyproject.toml --system

COPY . /app

RUN dos2unix /app/commands/*.sh
