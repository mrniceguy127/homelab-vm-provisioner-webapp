# db-interface microservice image (node only)
# Connects to an external PostgreSQL instance provided by homelab-vm-provisioner-db.
FROM node:20-bookworm-slim

WORKDIR /app

# Install production dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Copy application code
COPY src/ ./src/

# Configurable microservice port (default: 3002)
ARG DB_SERVICE_PORT=3002
ENV DB_SERVICE_PORT=${DB_SERVICE_PORT}
EXPOSE ${DB_SERVICE_PORT}

# Start the HTTP interface
CMD ["node", "src/server.js"]
