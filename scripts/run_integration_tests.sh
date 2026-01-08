#!/usr/bin/env bash
set -e

POSTGRES_USER="${POSTGRES_USER:-weather_user}"
POSTGRES_DB="${POSTGRES_DB:-weather_db}"

echo "===> Starting postgres for integration tests..."
docker compose up -d postgres

echo "===> Waiting for postgres to be ready..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    echo "Postgres is ready."
    break
  fi
  sleep 1
done

echo "===> Running integration tests inside bot container..."
docker compose run --rm bot pytest -m integration tests

echo "===> Stopping and cleaning up..."
docker compose down
