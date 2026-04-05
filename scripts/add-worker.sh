#!/usr/bin/env bash
set -euo pipefail

MASTER_IP="${1:?Usage: ./add-worker.sh <master-ip>}"
WORKER_NAME="${2:-worker-$(hostname -s)}"

echo "================================================"
echo "  White-Ops Worker Setup"
echo "================================================"
echo ""
echo "  Master: $MASTER_IP"
echo "  Worker: $WORKER_NAME"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[INSTALL] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "[OK] Docker installed. You may need to log out and back in."
fi

# Check connectivity
echo "[CHECK] Testing connection to master..."
if ! curl -sf "http://$MASTER_IP:8000/health" > /dev/null 2>&1; then
    echo "[ERROR] Cannot reach master at http://$MASTER_IP:8000"
    echo "  Make sure the master is running and port 8000 is accessible."
    exit 1
fi
echo "[OK] Master is reachable."

# Create worker directory
WORKER_DIR="$HOME/white-ops-worker"
mkdir -p "$WORKER_DIR"

# Create docker-compose for worker
cat > "$WORKER_DIR/docker-compose.yml" << EOF
services:
  worker:
    image: ghcr.io/white-ops/worker:latest
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - MASTER_URL=http://$MASTER_IP:8000
      - WORKER_NAME=$WORKER_NAME
      - WORKER_MAX_AGENTS=5
      - REDIS_HOST=$MASTER_IP
      - REDIS_PORT=6379
      - REDIS_PASSWORD=\${REDIS_PASSWORD:?Set REDIS_PASSWORD}
      - MINIO_ENDPOINT=$MASTER_IP:9000
      - MINIO_ROOT_USER=\${MINIO_ROOT_USER:-whiteops}
      - MINIO_ROOT_PASSWORD=\${MINIO_ROOT_PASSWORD:?Set MINIO_ROOT_PASSWORD}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY:-}
      - OPENAI_API_KEY=\${OPENAI_API_KEY:-}
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY:-}
      - OLLAMA_BASE_URL=\${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
      - DEFAULT_LLM_PROVIDER=\${DEFAULT_LLM_PROVIDER:-anthropic}
      - DEFAULT_LLM_MODEL=\${DEFAULT_LLM_MODEL:-claude-sonnet-4-20250514}
      - MAIL_SERVER_HOST=$MASTER_IP
      - MAIL_SERVER_PORT=8025
    restart: unless-stopped
EOF

echo ""
echo "[INFO] Worker configuration created at: $WORKER_DIR"
echo ""
echo "  Next steps:"
echo "  1. cd $WORKER_DIR"
echo "  2. Create .env with REDIS_PASSWORD and MINIO_ROOT_PASSWORD from master"
echo "  3. docker compose up -d"
echo "  4. Approve the worker in the admin panel: http://$MASTER_IP:3000/workers"
echo ""
