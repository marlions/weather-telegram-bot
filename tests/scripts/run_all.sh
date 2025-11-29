#!/usr/bin/env bash
set -e

echo "===> Step 1: running unit tests..."
docker compose run --rm bot pytest tests

echo
echo "===> Step 2: starting application (bot + postgres)..."
docker compose up --build
