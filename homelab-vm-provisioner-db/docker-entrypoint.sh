#!/bin/bash
set -e

# Service mode configuration (defaults to both)
ENABLE_DB="${ENABLE_DB:-true}"
ENABLE_DB_SERVICE="${ENABLE_DB_SERVICE:-true}"

# PostgreSQL connection details
HAS_MODULAR_DB_ENV=false
if [[ -n "${POSTGRES_HOST+x}" || -n "${POSTGRES_PORT+x}" || -n "${POSTGRES_USER+x}" || -n "${POSTGRES_PASSWORD+x}" || -n "${POSTGRES_DB+x}" ]]; then
    HAS_MODULAR_DB_ENV=true
fi

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-hlvmp}"
DB_PASSWORD="${POSTGRES_PASSWORD:-hlvmppass}"
DB_NAME="${POSTGRES_DB:-hlvmp}"

if [[ "$ENABLE_DB" == "true" ]]; then
    export POSTGRES_HOST=localhost
    export POSTGRES_PORT=5432
    export POSTGRES_USER="$DB_USER"
    export POSTGRES_PASSWORD="$DB_PASSWORD"
    export POSTGRES_DB="$DB_NAME"
elif [[ "$HAS_MODULAR_DB_ENV" == "true" ]]; then
    export POSTGRES_HOST="$DB_HOST"
    export POSTGRES_PORT="$DB_PORT"
    export POSTGRES_USER="$DB_USER"
    export POSTGRES_PASSWORD="$DB_PASSWORD"
    export POSTGRES_DB="$DB_NAME"
else
    unset POSTGRES_HOST POSTGRES_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB
fi

export PGHOST="${POSTGRES_HOST:-localhost}"
export PGPORT="${POSTGRES_PORT:-5432}"
export PGUSER="${POSTGRES_USER:-$DB_USER}"
export PGPASSWORD="${POSTGRES_PASSWORD:-$DB_PASSWORD}"
export PGDATABASE="${POSTGRES_DB:-$DB_NAME}"
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"

export DB_SERVICE_PORT="${DB_SERVICE_PORT:-3002}"
export DB_SERVICE_PASSWORD="${DB_SERVICE_PASSWORD:-changeme_db_secret}"

echo "==> Starting DB container"
echo "    ENABLE_DB:         $ENABLE_DB"
echo "    ENABLE_DB_SERVICE: $ENABLE_DB_SERVICE"
echo ""

# Validate at least one service is enabled
if [[ "$ENABLE_DB" != "true" && "$ENABLE_DB_SERVICE" != "true" ]]; then
    echo "ERROR: At least one of ENABLE_DB or ENABLE_DB_SERVICE must be true"
    exit 1
fi

# Ensure PGDATA directory exists and has correct permissions
mkdir -p "$PGDATA"
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

POSTGRES_PID=""
MICROSERVICE_PID=""

# Start PostgreSQL if enabled
if [[ "$ENABLE_DB" == "true" ]]; then
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
host all all 0.0.0.0/0 md5
local all all md5
EOF
        
        # Allow listening on all interfaces (exposed via Docker port mapping)
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
else
    echo "==> PostgreSQL disabled (ENABLE_DB=false)"
fi

# Start the microservice if enabled
if [[ "$ENABLE_DB_SERVICE" == "true" ]]; then
    echo "==> Starting DB microservice on port $DB_SERVICE_PORT..."
    node src/server.js &
    MICROSERVICE_PID=$!
else
    echo "==> DB microservice disabled (ENABLE_DB_SERVICE=false)"
fi

# Verify at least one service is running
if [[ -z "$POSTGRES_PID" && -z "$MICROSERVICE_PID" ]]; then
    echo "ERROR: No services started"
    exit 1
fi

# Handle shutdown gracefully
shutdown() {
    echo "==> Shutting down services..."
    if [[ -n "$MICROSERVICE_PID" ]]; then
        kill -TERM "$MICROSERVICE_PID" 2>/dev/null || true
    fi
    if [[ -n "$POSTGRES_PID" ]]; then
        kill -TERM "$POSTGRES_PID" 2>/dev/null || true
    fi
    if [[ -n "$MICROSERVICE_PID" ]]; then
        wait "$MICROSERVICE_PID" 2>/dev/null || true
    fi
    if [[ -n "$POSTGRES_PID" ]]; then
        wait "$POSTGRES_PID" 2>/dev/null || true
    fi
    exit 0
}

trap shutdown SIGTERM SIGINT

echo "==> Container ready"
echo ""
if [[ "$ENABLE_DB" == "true" ]]; then
    echo "PostgreSQL listening on port 5432"
fi
if [[ "$ENABLE_DB_SERVICE" == "true" ]]; then
    echo "DB microservice listening on port $DB_SERVICE_PORT"
fi
echo ""
echo "Press Ctrl+C to stop"

# Wait for either process to exit
wait -n
exit_code=$?

# If one process exits, shut down the other
shutdown
