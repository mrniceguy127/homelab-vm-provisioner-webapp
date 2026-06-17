#!/bin/bash
set -e

# PostgreSQL connection details (internal to container)
export PGHOST=localhost
export PGPORT=5432
export PGUSER="${POSTGRES_USER:-hlvmp}"
export PGPASSWORD="${POSTGRES_PASSWORD:-hlvmppass}"
export PGDATABASE="${POSTGRES_DB:-hlvmp}"
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"

# Microservice uses localhost PostgreSQL
export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@localhost:${PGPORT}/${PGDATABASE}"
export DB_SERVICE_PORT="${DB_SERVICE_PORT:-3002}"
export DB_SERVICE_PASSWORD="${DB_SERVICE_PASSWORD:-changeme_db_secret}"

echo "==> Starting PostgreSQL + DB Microservice container"

# Ensure PGDATA directory exists and has correct permissions
mkdir -p "$PGDATA"
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

# Initialize PostgreSQL data directory if it doesn't exist
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "==> Initializing PostgreSQL database..."
    
    # Create temporary password file
    PWFILE=$(mktemp)
    echo "$PGPASSWORD" > "$PWFILE"
    chmod 600 "$PWFILE"
    chown postgres:postgres "$PWFILE"
    
    # Initialize database
    gosu postgres initdb -D "$PGDATA" -U "$PGUSER" --pwfile="$PWFILE"
    
    # Remove password file
    rm -f "$PWFILE"
    
    # Configure PostgreSQL for local connections
    cat >> "$PGDATA/pg_hba.conf" <<EOF
host all all 127.0.0.1/32 md5
local all all md5
EOF
    
    # Allow listening on all interfaces (but only inside container)
    echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
fi

# Start PostgreSQL in the background as postgres user
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
    if [ $i -eq 30 ]; then
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

# Create migration_history table if it doesn't exist
psql -U "$PGUSER" -d "$PGDATABASE" -c "
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);"

# Apply pending migrations
for migration in migrations/*.sql; do
    if [ -f "$migration" ]; then
        filename=$(basename "$migration")
        
        # Check if migration already applied
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

# Start the microservice
echo "==> Starting DB microservice on port $DB_SERVICE_PORT..."
node src/server.js &
MICROSERVICE_PID=$!

# Handle shutdown gracefully
shutdown() {
    echo "==> Shutting down services..."
    kill -TERM "$MICROSERVICE_PID" 2>/dev/null || true
    kill -TERM "$POSTGRES_PID" 2>/dev/null || true
    wait "$MICROSERVICE_PID" "$POSTGRES_PID"
    exit 0
}

trap shutdown SIGTERM SIGINT

# Wait for either process to exit
wait -n
exit_code=$?

# If one process exits, shut down the other
shutdown
