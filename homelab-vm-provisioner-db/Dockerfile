# Multi-stage build for PostgreSQL + Node.js microservice
FROM postgres:17

# Install Node.js 20.x
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/

# Copy custom entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose microservice port (3002) and PostgreSQL port (5432)
EXPOSE 3002 5432

# Use custom entrypoint that starts PostgreSQL and/or the microservice
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
