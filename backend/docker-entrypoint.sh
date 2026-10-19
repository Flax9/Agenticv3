#!/bin/sh
# Jalankan migrasi database sebelum server start (matikan dengan RUN_MIGRATIONS=false)
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
fi
exec "$@"
