#!/usr/bin/env bash

# Exit script immediately if a critical command fails
set -e

echo "=== Checking Redis Status ==="

# 1. Check if redis-server is installed
if ! command -v redis-server 2>/dev/null; then
    echo "[-] Redis is not installed. Installing Redis Server..."
    sudo apt update
    sudo apt install -y redis-server
    echo "[+] Redis installed successfully!"
else
    echo "[+] Redis is already installed."
fi

# 2. Check if Redis server is running
echo "=== Checking if Redis service is active ==="

# Try pinging Redis via redis-cli
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "[+] Redis server is already running!"
else
    echo "[-] Redis is installed but NOT running. Starting Redis server..."
    
    # Check if systemd is available (standard Linux) or fallback to service command (WSL / Docker container)
    if command -v systemctl 2>/dev/null && systemctl is-systemd-running 2>/dev/null; then
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
    else
        sudo service redis-server start
    fi

    # Verify if it started successfully
    sleep 2
    if redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo "[+] Redis server started successfully!"
    else
        echo "[!] Failed to start Redis server. Please check your installation."
        exit 1
    fi
fi

echo "=== Everything is set! You can now run your Celery tasks. ==="