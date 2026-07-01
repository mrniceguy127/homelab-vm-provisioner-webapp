# Runtime Dockerfile for reverse proxy
# This container runs the Express proxy server
# Static files should be mounted or copied to /app/public

FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy source files
COPY src/ ./src/

# Create empty public directory (will be populated via volume or COPY)
#RUN mkdir -p public
COPY public/ ./public/

# Configurable proxy port (default: 3000)
ARG PROXY_PORT=3000
ENV PORT=${PROXY_PORT}
EXPOSE ${PROXY_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "const p=process.env.PORT||3000; require('http').get('http://localhost:'+p+'/proxy-health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); }).on('error', () => process.exit(1));"

# Start the proxy server
CMD ["node", "src/server.js"]
