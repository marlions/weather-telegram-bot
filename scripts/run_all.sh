#!/usr/bin/env bash
set -e

echo "===> Step 1: unit tests (excluding integration)..."
docker compose run --rm bot pytest -m "not integration" tests

echo
echo "===> Step 2: integration tests (postgres required)..."
POSTGRES_USER="${POSTGRES_USER:-weather_user}"
POSTGRES_DB="${POSTGRES_DB:-weather_db}"

docker compose up -d postgres
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker compose run --rm bot pytest -m integration tests
docker compose down

echo
echo "===> Step 3: starting application (bot + postgres)..."
docker compose up --build
