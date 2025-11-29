#!/usr/bin/env bash
set -e

echo "===> Building and starting services (bot + postgres)..."
docker compose up --build