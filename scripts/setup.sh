#!/usr/bin/env bash
set -euo pipefail

echo "================================================"
echo "  White-Ops - AI Workforce Platform Setup"
echo "================================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed. Please install Docker first."
    echo "  -> https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "[ERROR] Docker Compose is not installed."
    exit 1
fi

echo "[OK] Docker and Docker Compose found."

# Create .env if not exists
if [ ! -f .env ]; then
    echo "[SETUP] Creating .env from .env.example..."
    cp .env.example .env

    # Generate random secrets
    SECRET_KEY=$(openssl rand -hex 32)
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    REDIS_PASSWORD=$(openssl rand -hex 16)
    MINIO_PASSWORD=$(openssl rand -hex 16)

    if [[ "$OSTYPE" == "darwin"* ]]; then
        SED_CMD="sed -i ''"
    else
        SED_CMD="sed -i"
    fi

    $SED_CMD "s/SECRET_KEY=change-me/SECRET_KEY=$SECRET_KEY/" .env
    $SED_CMD "s/JWT_SECRET_KEY=change-me-to-a-different-random-string/JWT_SECRET_KEY=$JWT_SECRET_KEY/" .env
    $SED_CMD "s/POSTGRES_PASSWORD=change-me/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" .env
    $SED_CMD "s/REDIS_PASSWORD=change-me/REDIS_PASSWORD=$REDIS_PASSWORD/" .env
    $SED_CMD "s/MINIO_ROOT_PASSWORD=change-me-min-8-chars/MINIO_ROOT_PASSWORD=$MINIO_PASSWORD/" .env

    echo "[OK] .env created with random secrets."
    echo ""
    echo "  IMPORTANT: Edit .env to add your LLM API keys:"
    echo "    - ANTHROPIC_API_KEY"
    echo "    - OPENAI_API_KEY"
    echo "    - GOOGLE_API_KEY"
    echo ""
else
    echo "[OK] .env already exists."
fi

# Build and start
echo "[BUILD] Building Docker images..."
docker compose build

echo "[START] Starting services..."
docker compose up -d

echo ""
echo "================================================"
echo "  White-Ops is running!"
echo "================================================"
echo ""
echo "  Admin Panel:  http://localhost:3000"
echo "  API Server:   http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  MinIO Console:http://localhost:9001"
echo ""
echo "  Default Login:"
echo "    Email:    admin@whiteops.local"
echo "    Password: (check ADMIN_PASSWORD in .env)"
echo ""
echo "  To add a worker on another PC:"
echo "    curl -sSL http://$(hostname -I | awk '{print $1}'):8000/install | bash"
echo ""
echo "  Commands:"
echo "    make logs     - View logs"
echo "    make status   - Check status"
echo "    make down     - Stop all services"
echo ""
