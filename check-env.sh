#!/bin/bash
# Prerequisites check for Smart Attendance System
set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YELLOW}!${NC} $1"; }
ERRORS=0

echo "=== Smart Attendance System - Environment Check ==="
echo ""

# Python
if python3 --version &>/dev/null; then
  ok "Python: $(python3 --version)"
else
  fail "Python 3 not found"
fi

# Node
if command -v node &>/dev/null; then
  ok "Node.js: $(node --version)"
  ok "npm: $(npm --version)"
else
  fail "Node.js not installed. Run: brew install node"
fi

# Docker
if command -v docker &>/dev/null; then
  ok "Docker: $(docker --version)"
  if docker compose ps 2>/dev/null | grep -q smart-attendance-db; then
    ok "PostgreSQL container running"
  else
    warn "PostgreSQL container not running. Run: docker compose up -d"
  fi
else
  fail "Docker not installed. Install Docker Desktop from https://docker.com/products/docker-desktop"
fi

# PostgreSQL port
if nc -z localhost 5432 2>/dev/null; then
  ok "PostgreSQL accepting connections on port 5432"
else
  fail "PostgreSQL not reachable on port 5432"
fi

# Backend venv
if [ -x "backend/venv/bin/python" ]; then
  ok "Backend virtual environment ready ($(backend/venv/bin/python --version 2>&1))"
else
  warn "Backend venv not set up. Run: ./start-backend.sh (auto-creates venv)"
fi

# OpenCV face models
if [ -f "backend/uploads/models/face_detection_yunet_2023mar.onnx" ]; then
  ok "Face detection model downloaded"
else
  warn "Face models not yet downloaded (downloads on first face API call)"
fi

# Frontend deps
if [ -d "frontend/node_modules" ]; then
  ok "Frontend dependencies installed"
else
  warn "Frontend deps not installed. Run: cd frontend && npm install"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}Environment ready. Start with:${NC}"
  echo "  docker compose up -d"
  echo "  ./start-backend.sh"
  echo "  ./start-frontend.sh"
else
  echo -e "${RED}$ERRORS blocking issue(s) found. Fix above before starting.${NC}"
  exit 1
fi
