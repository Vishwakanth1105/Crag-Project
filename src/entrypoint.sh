#!/usr/bin/env bash
set -euo pipefail

# Wait for the application database to become reachable, apply pending
# migrations, then exec the requested command (uvicorn or worker loop).
python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url or url.startswith("sqlite"):
    sys.exit(0)

engine = create_engine(url, pool_pre_ping=True)
for attempt in range(90):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("database is ready", flush=True)
        break
    except Exception as exc:
        print(f"waiting for database ({attempt}): {exc}", flush=True)
        time.sleep(2)
else:
    raise SystemExit("database not reachable after timeout")
PY

echo "applying database migrations"
alembic upgrade head

exec "$@"
