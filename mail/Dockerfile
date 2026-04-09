FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir --target=/install aiosmtpd redis structlog

FROM python:3.12-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /install /usr/local/lib/python3.12/site-packages/

# Create non-root user
RUN groupadd -r whiteops && useradd -r -g whiteops -s /sbin/nologin whiteops

COPY --chown=whiteops:whiteops server.py .

USER whiteops

EXPOSE 8025

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',8025)); s.close()" || exit 1

CMD ["python", "server.py"]
