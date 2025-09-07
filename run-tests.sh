#!/bin/bash
# Convenience script to run tests using Docker Compose

set -e

echo "🧪 Running tests using Docker Compose..."

# Navigate to project root
cd "$(dirname "$0")"

# Run tests with Docker Compose
docker compose --profile test run --rm backend-test

echo "✅ Tests completed!"
