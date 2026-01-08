#!/usr/bin/env bash
set -e

echo "===> Running unit tests inside bot container (excluding integration)..."
docker compose run --rm bot pytest -m "not integration" tests

