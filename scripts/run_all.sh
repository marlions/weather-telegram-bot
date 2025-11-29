#!/usr/bin/env bash
set -e

echo "===> Step 1: unit tests..."
docker compose run --rm bot pytest tests

echo
echo "===> Step 2: integration tests..."
docker compose up -d postgres
docker compose run --rm bot pytest tests/test_integration_daily_weather.py
docker compose down

echo
echo "===> Step 3: starting application (bot + postgres)..."
docker compose up --build
