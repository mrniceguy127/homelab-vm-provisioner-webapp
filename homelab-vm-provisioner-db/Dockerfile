# Multi-stage build for PostgreSQL + Node.js microservice
# Stage 1: Get Node.js from official image
FROM node:20-bookworm-slim AS node

# Stage 2: Build final image with PostgreSQL + Node.js
FROM postgres:17

# Copy Node.js and npm completely from the Node image
COPY --from=node /usr/local/include/node /usr/local/include/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node /usr/local/bin /usr/local/bin
COPY --from=node /opt /opt

# Verify Node.js installation
RUN node --version && npm --version

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
