FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir aiosmtpd redis structlog

COPY server.py .

EXPOSE 8025

CMD ["python", "server.py"]
