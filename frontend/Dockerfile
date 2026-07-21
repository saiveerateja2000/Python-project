# Stage 1: Build React application
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package.json
COPY package.json ./

# Install dependencies
RUN npm install

# Copy application source
COPY . .

# Build React application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose Nginx port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:3000/ >/dev/null

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
