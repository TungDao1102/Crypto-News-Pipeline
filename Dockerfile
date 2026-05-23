FROM python:3.14-slim

LABEL org.opencontainers.image.title="Crypto News Pipeline"
LABEL org.opencontainers.image.description="Automated crypto news aggregation, AI processing, and multi-platform publishing pipeline"
LABEL org.opencontainers.image.source="https://github.com/crypto-news-pipeline/crypto-news-pipeline"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
