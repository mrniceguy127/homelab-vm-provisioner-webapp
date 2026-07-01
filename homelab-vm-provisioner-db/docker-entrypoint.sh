#!/bin/bash
set -e

# PostgreSQL connection details
DB_USER="${POSTGRES_USER:-hlvmp}"
DB_PASSWORD="${POSTGRES_PASSWORD:-hlvmppass}"
DB_NAME="${POSTGRES_DB:-hlvmp}"

# Inside the container PostgreSQL always runs locally on 5432
export PGHOST=localhost
export PGPORT=5432
export PGUSER="$DB_USER"
export PGPASSWORD="$DB_PASSWORD"
export PGDATABASE="$DB_NAME"
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"

echo "==> Starting PostgreSQL container"
echo "    Database: $DB_NAME"
echo "    User:     $DB_USER"
echo ""

# Ensure PGDATA directory exists and has correct permissions
mkdir -p "$PGDATA"
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

# Initialize PostgreSQL data directory if it doesn't exist
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "==> Initializing PostgreSQL database..."

    PWFILE=$(mktemp)
    echo "$PGPASSWORD" > "$PWFILE"
    chmod 600 "$PWFILE"
    chown postgres:postgres "$PWFILE"

    gosu postgres initdb -D "$PGDATA" -U "$PGUSER" --pwfile="$PWFILE"

    rm -f "$PWFILE"

    cat >> "$PGDATA/pg_hba.conf" <<EOF
host all all 127.0.0.1/32 md5
host all all 0.0.0.0/0 md5
local all all md5
EOF

    echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
fi

# Start PostgreSQL in the background as the postgres user
echo "==> Starting PostgreSQL server..."
gosu postgres postgres -D "$PGDATA" &
POSTGRES_PID=$!

# Wait for PostgreSQL to be ready
echo "==> Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if psql -U "$PGUSER" -d postgres -c "SELECT 1" >/dev/null 2>&1; then
        echo "==> PostgreSQL is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: PostgreSQL failed to start"
        exit 1
    fi
    sleep 1
done

# Create database if it doesn't exist
psql -U "$PGUSER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$PGDATABASE'" | grep -q 1 || \
    psql -U "$PGUSER" -d postgres -c "CREATE DATABASE $PGDATABASE"

# Run migrations
echo "==> Running database migrations..."
cd /app

psql -U "$PGUSER" -d "$PGDATABASE" -c "
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);"

for migration in migrations/*.sql; do
    if [ -f "$migration" ]; then
        filename=$(basename "$migration")
        applied=$(psql -U "$PGUSER" -d "$PGDATABASE" -tAc "SELECT COUNT(*) FROM migration_history WHERE filename='$filename'")
        if [ "$applied" = "0" ]; then
            echo "==> Applying migration: $filename"
            psql -U "$PGUSER" -d "$PGDATABASE" -f "$migration"
            psql -U "$PGUSER" -d "$PGDATABASE" -c "INSERT INTO migration_history (filename) VALUES ('$filename')"
        else
            echo "==> Skipping already applied migration: $filename"
        fi
    fi
done

# Handle shutdown gracefully
shutdown() {
    echo "==> Shutting down PostgreSQL..."
    kill -TERM "$POSTGRES_PID" 2>/dev/null || true
    wait "$POSTGRES_PID" 2>/dev/null || true
    exit 0
}

trap shutdown SIGTERM SIGINT

echo "==> Container ready"
echo ""
echo "PostgreSQL listening on port 5432"
echo ""
echo "Press Ctrl+C to stop"

# Wait for PostgreSQL to exit
wait "$POSTGRES_PID"
