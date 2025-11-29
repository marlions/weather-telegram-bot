#!/usr/bin/env bash
set -e

echo "===> Running unit tests inside bot container..."
docker compose run --rm bot pytest tests
