#!/usr/bin/env bash
set -euo pipefail

# WhiteOps Automated Backup
# Cron: 0 2 * * * /opt/whiteops/scripts/backup-cron.sh

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/backup.log"

mkdir -p "$BACKUP_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# PostgreSQL backup
log "Starting PostgreSQL backup..."
PGFILE="${BACKUP_DIR}/whiteops_pg_${TIMESTAMP}.sql.gz"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-whiteops}" "${POSTGRES_DB:-whiteops}" | gzip > "$PGFILE"
log "PostgreSQL backup complete: $PGFILE ($(du -h "$PGFILE" | cut -f1))"

# Redis backup
log "Starting Redis backup..."
docker compose exec -T redis redis-cli -a "${REDIS_PASSWORD}" BGSAVE
sleep 2
docker compose cp redis:/data/dump.rdb "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
log "Redis backup complete"

# MinIO backup (if mc is available)
if command -v mc &>/dev/null; then
  log "Starting MinIO backup..."
  mc mirror "whiteops/${MINIO_BUCKET:-whiteops-files}" "${BACKUP_DIR}/minio_${TIMESTAMP}/" --quiet
  log "MinIO backup complete"
fi

# Cleanup old backups
log "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "whiteops_*" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "redis_*" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

log "Backup completed successfully"
