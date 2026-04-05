#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo -e "  ${GREEN}PASS${NC}  $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}  $desc"
        FAIL=$((FAIL + 1))
    fi
}

warn() {
    local desc="$1"
    echo -e "  ${YELLOW}WARN${NC}  $desc"
    WARN=$((WARN + 1))
}

echo ""
echo "=========================================="
echo "  White-Ops Pre-Deployment Check"
echo "=========================================="
echo ""

# ---- Prerequisites ----
echo "Prerequisites:"
command -v docker &>/dev/null
check "Docker installed" $?

docker compose version &>/dev/null 2>&1
check "Docker Compose installed" $?

echo ""

# ---- Environment ----
echo "Environment:"
if [ -f .env ]; then
    check ".env file exists" 0

    source .env 2>/dev/null || true

    if [ -n "${SECRET_KEY:-}" ] && [ "$SECRET_KEY" != "change-me" ]; then
        check "SECRET_KEY is set and not default" 0
    else
        check "SECRET_KEY is set and not default" 1
    fi

    if [ -n "${JWT_SECRET_KEY:-}" ] && [ "$JWT_SECRET_KEY" != "change-me-to-a-different-random-string" ]; then
        check "JWT_SECRET_KEY is set and not default" 0
    else
        check "JWT_SECRET_KEY is set and not default" 1
    fi

    if [ -n "${POSTGRES_PASSWORD:-}" ] && [ "$POSTGRES_PASSWORD" != "change-me" ]; then
        check "POSTGRES_PASSWORD is not default" 0
    else
        check "POSTGRES_PASSWORD is not default" 1
    fi

    if [ -n "${REDIS_PASSWORD:-}" ] && [ "$REDIS_PASSWORD" != "change-me" ]; then
        check "REDIS_PASSWORD is not default" 0
    else
        check "REDIS_PASSWORD is not default" 1
    fi

    if [ -n "${ADMIN_PASSWORD:-}" ] && [ "$ADMIN_PASSWORD" != "change-me" ]; then
        check "ADMIN_PASSWORD is not default" 0
    else
        check "ADMIN_PASSWORD is not default" 1
    fi

    # LLM keys
    if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ] || [ -n "${GOOGLE_API_KEY:-}" ]; then
        check "At least one LLM API key configured" 0
    else
        warn "No LLM API keys configured (agents won't be able to use cloud LLMs)"
    fi

    # CORS
    if [ "${CORS_ORIGINS:-}" = "http://localhost:3000" ]; then
        warn "CORS_ORIGINS is still localhost (update for production domain)"
    fi
else
    check ".env file exists" 1
fi

echo ""

# ---- Docker Images ----
echo "Docker Images:"
if docker compose config --quiet 2>/dev/null; then
    check "docker-compose.yml is valid" 0
else
    check "docker-compose.yml is valid" 1
fi

echo ""

# ---- Security ----
echo "Security:"

# Check for hardcoded secrets in code
if ! grep -rn "password.*=.*['\"]changeme['\"]" server/app/ worker/agent/ --include="*.py" 2>/dev/null | grep -v "config.py\|\.env" | head -1 > /dev/null 2>&1; then
    check "No hardcoded 'changeme' passwords in code" 0
else
    check "No hardcoded 'changeme' passwords in code" 1
fi

# Check .gitignore includes .env
if grep -q "^\.env$" .gitignore 2>/dev/null; then
    check ".env is in .gitignore" 0
else
    check ".env is in .gitignore" 1
fi

# Check no .env committed
if ! git ls-files --error-unmatch .env 2>/dev/null; then
    check ".env is not tracked by git" 0
else
    check ".env is not tracked by git" 1
fi

echo ""

# ---- Files ----
echo "Project Structure:"
check "Server Dockerfile exists" $(test -f server/Dockerfile && echo 0 || echo 1)
check "Worker Dockerfile exists" $(test -f worker/Dockerfile && echo 0 || echo 1)
check "Web Dockerfile exists" $(test -f web/Dockerfile && echo 0 || echo 1)
check "Mail Dockerfile exists" $(test -f mail/Dockerfile && echo 0 || echo 1)
check "CI workflow exists" $(test -f .github/workflows/ci.yml && echo 0 || echo 1)

echo ""

# ---- Summary ----
TOTAL=$((PASS + FAIL + WARN))
echo "=========================================="
echo "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "=========================================="
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}Deployment NOT recommended. Fix failed checks first.${NC}"
    exit 1
elif [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}Deployment possible but review warnings.${NC}"
    exit 0
else
    echo -e "${GREEN}All checks passed. Ready for deployment.${NC}"
    exit 0
fi
