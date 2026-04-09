FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libreoffice-calc \
    libreoffice-writer \
    libreoffice-impress \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r whiteops && useradd -r -g whiteops -d /app -s /sbin/nologin whiteops
WORKDIR /app
COPY --from=builder /install /usr/local
RUN playwright install chromium --with-deps
COPY agent/ agent/
RUN chown -R whiteops:whiteops /app
USER whiteops
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "-m", "agent.main"]
