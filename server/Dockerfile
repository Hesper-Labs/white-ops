FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r whiteops && useradd -r -g whiteops -d /app -s /sbin/nologin whiteops
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/
RUN chown -R whiteops:whiteops /app
USER whiteops
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
