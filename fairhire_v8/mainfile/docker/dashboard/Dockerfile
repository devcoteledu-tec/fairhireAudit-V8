# Multi-stage build for React dashboard
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package management files
COPY fairhire/dashboard/package*.json ./

# Install packages
RUN npm ci

# Copy the dashboard source code
COPY fairhire/dashboard/ ./

# Accept build arguments for environment variables
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the static React distribution files
RUN npm run build

# --- Stage 2: Serve using Nginx ---
FROM nginx:alpine

# Copy custom reverse-proxy config
COPY docker/dashboard/nginx.conf /etc/nginx/conf.d/default.conf

# Copy build files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
