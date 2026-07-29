#!/usr/bin/env bash

# Exit on error
set -e

CONTAINER_NAME="neo4j"
IMAGE_NAME="neo4j:latest"
DATA_DIR="$HOME/neo4j/data"

# Ensure host data directory exists
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
    exit 0
fi

# 3. If container does not exist: Pull and Run
echo "Container '${CONTAINER_NAME}' not found. Pulling latest image..."
docker pull "$IMAGE_NAME"

echo "Running new '${CONTAINER_NAME}' container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --publish=7474:7474 \
    --publish=7687:7687 \
    --volume="$DATA_DIR":/data \
    "$IMAGE_NAME"

echo "Neo4j is up and running!"
echo "Neo4j dashboard localhost:7687"