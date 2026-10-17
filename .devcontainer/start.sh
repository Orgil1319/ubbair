#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
test -f .env || cp .env.example .env
for i in $(seq 1 60); do
  docker info >/dev/null 2>&1 && break
  sleep 2
done
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
