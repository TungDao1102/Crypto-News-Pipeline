#!/bin/sh
set -e

echo "=== Crypto News Pipeline Entrypoint ==="

for f in sources.json .env; do
    if [ ! -f "$f" ]; then
        echo "ERROR: $f not found. Mount as a volume."
        exit 1
    fi
done

if grep -q "your_" .env 2>/dev/null; then
    echo "ERROR: .env contains placeholder values. Replace with real credentials."
    exit 1
fi

mkdir -p logs
mkdir -p session

ln -sf /app/session/telegram.session /app/telegram.session

echo "Entrypoint validation passed. Starting pipeline..."
exec python -m src.main
