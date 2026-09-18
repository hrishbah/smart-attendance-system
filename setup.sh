#!/bin/bash
set -euo pipefail

echo "=== Smart Attendance System Setup ==="

# Fix Homebrew permissions if needed
if [ -d /usr/local/Homebrew ] && [ ! -w /usr/local/Homebrew ]; then
  echo "NOTE: Homebrew may need permission fix:"
  echo "  sudo chown -R \$(whoami) /usr/local/Cellar /usr/local/Homebrew /usr/local/bin /usr/local/lib /usr/local/share"
fi

# Node.js
if ! command -v node &>/dev/null; then
  echo "Installing Node.js via Homebrew..."
  brew install node || { echo "Please run: brew install node"; exit 1; }
fi
echo "Node: $(node --version)"

# Docker check
if ! command -v docker &>/dev/null; then
  echo ""
  echo "ERROR: Docker is required for PostgreSQL."
  echo "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
  echo "Then run: docker compose up -d"
  exit 1
fi

# PostgreSQL via Docker
echo "Starting PostgreSQL..."
docker compose up -d
sleep 5

# Backend
echo "Setting up backend..."
cd backend
if [ ! -x "venv/bin/python" ]; then
  python3 -m venv venv
  venv/bin/python -m pip install --upgrade pip
  venv/bin/python -m pip install -r requirements.txt
fi
cp -n ../.env.example .env 2>/dev/null || true
cd ..

# Frontend
echo "Setting up frontend..."
cd frontend
npm install
cd ..

chmod +x check-env.sh start-backend.sh start-frontend.sh

echo ""
echo "=== Setup Complete ==="
./check-env.sh
