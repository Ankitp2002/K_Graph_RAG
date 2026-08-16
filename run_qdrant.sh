#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

CONTAINER_NAME="qdrant"
IMAGE_NAME="qdrant/qdrant:latest"
DATA_DIR="$HOME/qdrant/storage"

# Ensure host storage directory exists
mkdir -p "$DATA_DIR"

# 1. Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '${CONTAINER_NAME}' is already running."
    exit 0
fi

# 2. Check if container exists but is stopped
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Container '${CONTAINER_NAME}' exists but is stopped. Starting it..."
    docker start "$CONTAINER_NAME"
    echo "Container '${CONTAINER_NAME}' started successfully."
    echo "REST API & Web UI: http://localhost:6333/dashboard"
    echo "gRPC API: localhost:6334"
    exit 0
fi

# 3. If container does not exist: Pull and Run
echo "Container '${CONTAINER_NAME}' not found. Pulling latest image..."
docker pull "$IMAGE_NAME"

echo "Running new '${CONTAINER_NAME}' container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --publish=6333:6333 \
    --publish=6334:6334 \
    --volume="$DATA_DIR":/qdrant/storage \
    "$IMAGE_NAME"

echo "Qdrant is up and running!"
echo "REST API & Web UI: http://localhost:6333/dashboard"
echo "gRPC API: localhost:6334"