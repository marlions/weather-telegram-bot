#!/usr/bin/env bash
set -e

echo "===> Starting postgres for integration tests..."
docker compose up -d postgres

echo "===> Running integration tests inside bot container..."
docker compose run --rm bot pytest tests/test_integration_daily_weather.py

echo "===> Stopping and cleaning up..."
docker compose down
