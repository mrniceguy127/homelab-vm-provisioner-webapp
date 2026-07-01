# PostgreSQL image for the provisioner store.
# Bakes in migrations and a custom entrypoint that initializes the database
# and applies migrations on first startup.
FROM postgres:17

# Copy migrations and custom entrypoint
COPY migrations/ /app/migrations/
COPY docker-entrypoint.sh /usr/local/bin/hlvmp-docker-entrypoint.sh
RUN chmod +x /usr/local/bin/hlvmp-docker-entrypoint.sh

# Expose PostgreSQL port
EXPOSE 5432

# Custom entrypoint starts PostgreSQL and runs migrations
ENTRYPOINT ["/usr/local/bin/hlvmp-docker-entrypoint.sh"]
