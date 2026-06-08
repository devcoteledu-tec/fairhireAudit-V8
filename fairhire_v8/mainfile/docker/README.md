# FairHire Docker Setup

This directory contains the production-ready Docker configuration for the FairHire AI-powered hiring compliance platform. 

The Docker setup builds and orchestrates two services:
1. **Backend API**: A FastAPI service running on Python 3.11-slim, optimized using a multi-stage build, health checking, and non-root execution.
2. **Dashboard SPA**: A React 19 + Vite 8 frontend compiled with Node 22-alpine and served via a hardened Nginx alpine image that handles routing and acts as a reverse proxy for the API.

---

## Prerequisites

Ensure you have the following installed on your host system:
- [Docker](https://docs.docker.com/get-docker/) (v20.10.0 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0.0 or later)

---

## Directory Structure

```
docker/
├── docker-compose.yml          # Services orchestrator (Backend & Dashboard)
├── .env.example                # Template file for environment variables
├── README.md                   # Setup and usage documentation
├── backend/
│   ├── Dockerfile              # Multi-stage Python FastAPI build
│   ├── .dockerignore           # Excludes python virtualenvs, caches, etc.
│   └── requirements.docker.txt # Pinned Python dependencies (adds missing scipy/numpy)
└── dashboard/
    ├── Dockerfile              # Multi-stage React + Nginx build
    ├── .dockerignore           # Excludes node_modules and logs
    └── nginx.conf              # Hardened Nginx production reverse proxy config
```

---

## Quick Start

### 1. Configure the Environment

Copy the environment template to `.env` inside the `docker` directory:

```bash
cp docker/.env.example docker/.env
```

Open `docker/.env` and configure the values:
- **`DATABASE_URL`**: Your Supabase/PostgreSQL connection string.
- **`JWT_SECRET`**: A cryptographically secure random string (minimum 32 characters).
- **`GEMINI_API_KEY`**: Your Gemini API key for bias audits and text generation.
- **`ALLOWED_ORIGINS`**: Set to `http://localhost` for standard docker compose deployments.

### 2. Build and Start the Application

To build the images and run the containerized application in the background:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build -d
```

*Note: The `--env-file` parameter ensures Docker Compose loads your environment file from the correct location.*

### 3. Verify services are active

- **Dashboard**: `http://localhost`
- **Backend API**: `http://localhost:8080/api/health`

---

## Production Security & Hardening Features

- **Multi-Stage Builds**: Drastically reduces image sizes. Compiler dependencies (`build-essential`, `node-modules` dev deps) are discarded in the final runtime images.
- **Least Privilege User**: The backend application executes under a dedicated non-root user (`appuser` with PID `10001`) preventing potential host escalation attacks.
- **Integrated Reverse Proxy**: Nginx routes all `/api` traffic internally to the FastAPI backend, eliminating CORS configuration complexity.
- **Production Headers**: Nginx is pre-configured with security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`).
- **Resource Constraints**: Docker Compose limits CPU and Memory allocation for each container to prevent denial-of-service (DoS) states on the host system.
- **Native Health Checking**: Healthy status checks evaluate endpoints (`/api/health` and `/healthz`) before allowing traffic.

---

## Useful CLI Commands

### Viewing Logs
```bash
docker compose -f docker/docker-compose.yml logs -f
```

### Stopping the Services
```bash
docker compose -f docker/docker-compose.yml down
```

### Checking Container Status
```bash
docker compose -f docker/docker-compose.yml ps
```

### Testing Nginx Configuration inside container
```bash
docker exec -it fairhire-dashboard nginx -t
```
