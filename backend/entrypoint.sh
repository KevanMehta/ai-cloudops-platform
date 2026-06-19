#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import os, sys, time
import psycopg2
url = os.environ.get('DATABASE_URL', '')
for i in range(30):
    try:
        psycopg2.connect(url)
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
"; do
  sleep 1
done

echo "Running database initialization..."
python -m app.seed.init_db

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
