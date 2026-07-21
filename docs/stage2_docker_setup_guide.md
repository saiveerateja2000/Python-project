# Stage 2 Guide - Dockerize Every Service Individually

## 1) Objective
Transform each service (frontend, users API, orders API, and database) into independently runnable Docker containers while keeping them communicating via REST APIs and a shared external PostgreSQL database.

## 2) Why this concept exists
Containerization achieves:
- **Reproducibility**: "Works on my machine" becomes "works everywhere"
- **Isolation**: Services don't conflict with host system dependencies
- **Portability**: Same image runs locally, in CI/CD, and in production
- **Foundation for orchestration**: Prepares for Stage 3 (Docker Compose) and Stage 4 (Kubernetes)

## 3) Production problem this solves
- Development/production parity: eliminates environment drift
- Dependency hell: each service declares its exact requirements
- Fast onboarding: new engineers clone repo, run Docker, no manual setup
- Reproducible CI/CD: every pipeline stage uses identical images

## 4) How companies use it
- Netflix, Uber, Airbnb: containerize every microservice independently before orchestration
- CI/CD pipelines: build once, test in container, deploy same image to staging and production
- Local development: engineers run `docker build` and `docker run` for fast feedback

## 5) Interview expectations
You should explain why each service has its own Dockerfile, how multi-stage builds reduce image size, and why health checks are essential.

## 6) Common mistakes
- Not using `.dockerignore` (adds unnecessary files to images)
- Missing health checks (containers appear running but services are dead)
- Hardcoding port numbers in application code instead of using environment variables
- Using `latest` tag (no version tracking, unpredictable behavior)
- Not setting `user` in Dockerfile (runs as root, security risk)
- Not using multi-stage builds (bloated frontend image)
- Ignoring signal handling (containers don't shut down gracefully)

## 7) Troubleshooting techniques
- `docker build -t name . --no-cache` (rebuild without cache)
- `docker run -it <image> sh` (shell into container to debug)
- `docker logs <container>` (view container stdout/stderr)
- `docker exec <container> curl http://localhost:5001/health` (test health endpoint)
- `docker inspect <container>` (view full container configuration)
- Check `.dockerignore` if build context is too large
- Use `docker stats` to monitor resource usage

## 8) Implementation steps

### 8.1) Prerequisites
- Docker Desktop installed and running (or Docker Engine on Linux)
- Docker CLI available in terminal
- Your repository cloned locally

Verify Docker installation:
```bash
docker --version
docker run hello-world
```

### 8.2) Build PostgreSQL Database Container

Navigate to repository root:
```bash
cd /path/to/Python-project
```

Build database image:
```bash
docker build -f database/Dockerfile -t devops-db:1.0 .
```

Verify build:
```bash
docker images | grep devops-db
```

**Understanding the build:**
- `database/Dockerfile` uses official `postgres:15-alpine` as base
- Copies `database/init.sql` to `/docker-entrypoint-initdb.d/`
- PostgreSQL automatically runs all `.sql` files in that directory on first startup
- `--tag devops-db:1.0` creates a named image with semantic versioning

### 8.3) Build Users Service Container

Build users service image:
```bash
docker build -f services/users_service/Dockerfile -t devops-users:1.0 .
```

Verify build:
```bash
docker images | grep devops-users
```

**Understanding the build:**
- `services/users_service/Dockerfile` uses `python:3.11-slim` (lighter than full Python image)
- Installs system dependencies (gcc for psycopg2 compilation, postgresql-client for CLI tools)
- Copies only `requirements.txt` first (Docker layer caching: dependencies layer is reused if code doesn't change)
- Copies application code last (code layer changes frequently, previous layers cached)
- Exposes port 5001 (metadata, doesn't actually publish the port)
- Health check runs every 30s: connects to `/health` endpoint
- `CMD ["python", "-u", "app.py"]` runs Flask app with unbuffered output (critical for Docker logging)

### 8.4) Build Orders Service Container

Build orders service image:
```bash
docker build -f services/orders_service/Dockerfile -t devops-orders:1.0 .
```

Verify build:
```bash
docker images | grep devops-orders
```

**Understanding the build:**
- Same Python setup as users service
- Different port (5002) and health check endpoint
- Includes `requests` library dependency for inter-service communication

### 8.5) Build Frontend Container

Build frontend image (multi-stage build):
```bash
docker build -f frontend/Dockerfile -t devops-frontend:1.0 .
```

Verify build:
```bash
docker images | grep devops-frontend
```

**Understanding the build:**
- **Stage 1** (builder): `node:20-alpine` installs dependencies and builds React app
  - Runs `npm ci` (clean install, preferred in CI/CD over `npm install`)
  - Runs `npm run build` (produces optimized `/dist` folder)
  - This stage is discarded after build; final image doesn't include Node.js or source code
  
- **Stage 2** (runtime): `nginx:alpine` serves built assets
  - Copies only `/dist` from builder stage (final image is ~30MB instead of ~400MB)
  - Includes `nginx.conf` for proper routing and compression
  - Nginx serves static files at port 3000
  - Health check uses `wget` to verify frontend responds

**Why multi-stage?**
- Reduces final image from ~400MB (with Node.js + source) to ~30MB
- Smaller images = faster pulls, less storage, faster container startup
- Production doesn't need Node.js, only the built assets

## 9) Running containers individually

### 9.1) Run PostgreSQL Database

**Create and run database container:**
```bash
docker run -d \
  --name devops-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=devops_project \
  -p 5432:5432 \
  devops-db:1.0
```

**Flags explained:**
- `-d`: run in detached mode (background)
- `--name devops-postgres`: container name for reference
- `-e POSTGRES_PASSWORD=postgres`: set database password
- `-e POSTGRES_DB=devops_project`: create database named `devops_project`
- `-p 5432:5432`: map container port 5432 to host port 5432
- `devops-db:1.0`: image name and tag

**Verify database is running:**
```bash
docker logs devops-postgres
docker exec devops-postgres psql -U postgres -d devops_project -c "\dt"
```

Expected output:
- Logs show PostgreSQL initialization messages
- `\dt` command lists tables: `users` and `orders`

**Health check:**
```bash
docker ps | grep devops-postgres
```

Status should show `(healthy)` after ~10 seconds.

### 9.2) Run Users Service

**Create and run users service container:**
```bash
docker run -d \
  --name devops-users \
  -e DATABASE_URL="postgresql://postgres:postgres@devops-postgres:5432/devops_project" \
  -e USERS_SERVICE_PORT=5001 \
  -p 5001:5001 \
  --link devops-postgres \
  devops-users:1.0
```

**Flags explained:**
- `--name devops-users`: container name
- `-e DATABASE_URL=...`: connection string to PostgreSQL
  - Host is `devops-postgres` (container name)
  - Uses internal Docker network for container-to-container communication
  - Port is 5432 (internal, not exposed)
- `--link devops-postgres`: connects to postgres container (legacy feature, modern approach uses networks)
- `-p 5001:5001`: expose port 5001 on host

**Verify service is running:**
```bash
docker logs devops-users
curl http://localhost:5001/health
```

Expected output:
- Logs show Flask startup message
- `curl` returns: `{"status":"ok","service":"users-service"}`

**Test API:**
```bash
curl -X POST http://localhost:5001/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com"}'
```

Expected: `201 Created` with user data

### 9.3) Run Orders Service

**Create and run orders service container:**
```bash
docker run -d \
  --name devops-orders \
  -e DATABASE_URL="postgresql://postgres:postgres@devops-postgres:5432/devops_project" \
  -e USERS_SERVICE_URL="http://devops-users:5001" \
  -e ORDERS_SERVICE_PORT=5002 \
  -p 5002:5002 \
  --link devops-postgres \
  --link devops-users \
  devops-orders:1.0
```

**Flags explained:**
- `-e USERS_SERVICE_URL=http://devops-users:5001`: tells orders service where to find users service
  - Use container name (not localhost) for inter-container communication
- `--link devops-users`: connects to users service

**Verify service is running:**
```bash
docker logs devops-orders
curl http://localhost:5002/health
```

Expected output:
- Logs show Flask startup
- `curl` returns: `{"status":"ok","service":"orders-service"}`

**Test API:**
```bash
# Create an order for user 1 (created in previous step)
curl -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"item":"Laptop","quantity":1}'
```

Expected: `201 Created` with order data

### 9.4) Run Frontend Container

**Create and run frontend container:**
```bash
docker run -d \
  --name devops-frontend \
  -e VITE_USERS_API_URL="http://localhost:5001" \
  -e VITE_ORDERS_API_URL="http://localhost:5002" \
  -p 3000:3000 \
  devops-frontend:1.0
```

**Flags explained:**
- `-e VITE_USERS_API_URL=...`: frontend environment variable for users service API
- `-e VITE_ORDERS_API_URL=...`: frontend environment variable for orders service API
- `-p 3000:3000`: expose Nginx on port 3000

**Verify frontend is running:**
```bash
docker logs devops-frontend
curl http://localhost:3000
```

Expected output:
- Logs show Nginx startup
- `curl` returns HTML with React app

**Access frontend in browser:**
Open `http://localhost:3000` in your web browser.

Expected:
- Page title "Cloud Native Project - Stage 1 (Local)"
- Users form and orders form visible
- Can create users and orders
- Lists display created data

## 10) Cleanup: Stop and remove containers

**Stop all running containers:**
```bash
docker stop devops-frontend devops-orders devops-users devops-postgres
```

**Remove all containers:**
```bash
docker rm devops-frontend devops-orders devops-users devops-postgres
```

**Remove all images:**
```bash
docker rmi devops-frontend:1.0 devops-orders:1.0 devops-users:1.0 devops-db:1.0
```

**Verify cleanup:**
```bash
docker ps -a
docker images | grep devops
```

Both should return empty results.

## 11) Environment variables explained

**Database:**
- `POSTGRES_PASSWORD`: password for postgres superuser
- `POSTGRES_DB`: database name to create on startup
- `POSTGRES_USER`: defaults to `postgres`

**Users Service:**
- `DATABASE_URL`: PostgreSQL connection string
  - Format: `postgresql://user:password@host:port/database`
- `USERS_SERVICE_PORT`: port Flask listens on (default: 5001)

**Orders Service:**
- `DATABASE_URL`: PostgreSQL connection string
- `USERS_SERVICE_URL`: HTTP endpoint of users service (for validation)
- `ORDERS_SERVICE_PORT`: port Flask listens on (default: 5002)

**Frontend:**
- `VITE_USERS_API_URL`: backend API URL for users service
- `VITE_ORDERS_API_URL`: backend API URL for orders service
- These are baked into the build, not read at runtime (Vite is a build tool)

## 12) Docker Networking Concepts

**--link (legacy, deprecated but still works):**
```bash
docker run --link <container_name> <image>
```
- Creates entry in `/etc/hosts` inside container
- Allows container to reach linked container by name
- Only works with `docker run`, not `docker-compose` by default
- Deprecated in favor of custom networks

**Modern approach (custom networks):**
```bash
docker network create devops-network
docker run --network devops-network --name devops-postgres <image>
docker run --network devops-network -e DATABASE_URL=postgresql://postgres@devops-postgres:5432 <image>
```
- More flexible, recommended for production
- Used by Docker Compose (coming in Stage 3)

## 13) Debugging container issues

**View logs:**
```bash
docker logs <container_name>
docker logs -f <container_name>  # follow logs (like tail -f)
docker logs --tail 50 <container_name>  # last 50 lines
```

**Execute command inside running container:**
```bash
docker exec -it <container_name> sh
docker exec <container_name> curl http://localhost:5001/health
docker exec <container_name> psql -U postgres -d devops_project -c "SELECT COUNT(*) FROM users;"
```

**Inspect container configuration:**
```bash
docker inspect <container_name>
docker inspect <container_name> | grep -A 10 "IPAddress"
```

**Check resource usage:**
```bash
docker stats <container_name>
docker stats  # all containers
```

**View container processes:**
```bash
docker top <container_name>
```

## 14) Every Dockerfile explained

### Frontend (`frontend/Dockerfile`)
```dockerfile
FROM node:20-alpine AS builder
```
- Base image: Node.js 20 on Alpine Linux (minimal, ~40MB base)
- `AS builder`: names this stage for multi-stage build

```dockerfile
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
```
- Working directory inside container
- Copy package files (locked versions ensure reproducible builds)
- `npm ci` (clean install) preferred over `npm install` in Docker

```dockerfile
COPY . .
RUN npm run build
```
- Copy all source code
- Build optimized production bundle to `/app/dist`

```dockerfile
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```
- Second stage: fresh nginx container
- Copy only the built assets from builder stage
- First stage (with Node.js and source code) is discarded
- Result: final image is ~30MB instead of ~400MB

### Users Service (`services/users_service/Dockerfile`)
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client
```
- Base image: Python 3.11 slim (minimal, no unnecessary tools)
- Install gcc (needed to compile psycopg2 C extension)
- Install postgresql-client (for debugging with `psql` command)

```dockerfile
COPY services/users_service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY services/users_service/ ./
```
- Copy requirements first (layer is cached if requirements don't change)
- Install dependencies
- Copy source code last (code changes frequently, but dependency layer is cached)

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5001/health', timeout=2)" || exit 1
```
- Every 30s, make HTTP request to health endpoint
- If 3 consecutive requests fail, mark container as unhealthy
- Start period of 5s gives app time to start before first check

### Orders Service (`services/orders_service/Dockerfile`)
- Identical pattern to users service, different port (5002)

### Database (`database/Dockerfile`)
```dockerfile
FROM postgres:15-alpine
COPY database/init.sql /docker-entrypoint-initdb.d/
```
- Base image: official PostgreSQL 15 Alpine
- Copy init script to special directory
- PostgreSQL automatically runs all .sql files in that directory on first startup
- User doesn't need to run `psql -f init.sql` manually

## 15) How to verify success

**All containers running:**
```bash
docker ps
```
Expected: 4 containers (devops-postgres, devops-users, devops-orders, devops-frontend)

**All health checks passing:**
```bash
docker ps
```
Expected: `(healthy)` status for all containers

**Database connectivity:**
```bash
docker exec devops-postgres psql -U postgres -d devops_project -c "SELECT COUNT(*) FROM users;"
```
Expected: `0` (no users yet)

**Users API working:**
```bash
curl http://localhost:5001/health
curl http://localhost:5001/users
```
Expected: `{"status":"ok","service":"users-service"}` and `[]`

**Orders API working:**
```bash
curl http://localhost:5002/health
curl http://localhost:5002/orders
```
Expected: `{"status":"ok","service":"orders-service"}` and `[]`

**Frontend working:**
```bash
curl http://localhost:3000 | head -20
```
Expected: HTML with React app

**Full integration test:**
```bash
# Create user
USER_RESPONSE=$(curl -s -X POST http://localhost:5001/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com"}')
echo $USER_RESPONSE

# Create order for that user
curl -s -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"item":"Laptop","quantity":1}' | jq .

# Verify in frontend: Open http://localhost:3000 in browser
```

## 16) Only then continue

After all containers run successfully and pass health checks:
- Stage 3: Docker Compose (orchestrate all containers with single `docker-compose up`)
- Stage 4: Kubernetes (deploy to production-grade container orchestration)

---

## Quick Reference Commands

```bash
# Build images
docker build -f database/Dockerfile -t devops-db:1.0 .
docker build -f services/users_service/Dockerfile -t devops-users:1.0 .
docker build -f services/orders_service/Dockerfile -t devops-orders:1.0 .
docker build -f frontend/Dockerfile -t devops-frontend:1.0 .

# Start all containers
docker run -d --name devops-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=devops_project -p 5432:5432 devops-db:1.0
docker run -d --name devops-users -e DATABASE_URL="postgresql://postgres:postgres@devops-postgres:5432/devops_project" -e USERS_SERVICE_PORT=5001 -p 5001:5001 --link devops-postgres devops-users:1.0
docker run -d --name devops-orders -e DATABASE_URL="postgresql://postgres:postgres@devops-postgres:5432/devops_project" -e USERS_SERVICE_URL="http://devops-users:5001" -e ORDERS_SERVICE_PORT=5002 -p 5002:5002 --link devops-postgres --link devops-users devops-orders:1.0
docker run -d --name devops-frontend -e VITE_USERS_API_URL="http://localhost:5001" -e VITE_ORDERS_API_URL="http://localhost:5002" -p 3000:3000 devops-frontend:1.0

# View logs
docker logs -f devops-postgres
docker logs -f devops-users
docker logs -f devops-orders
docker logs -f devops-frontend

# Stop all
docker stop devops-frontend devops-orders devops-users devops-postgres

# Clean up
docker rm devops-frontend devops-orders devops-users devops-postgres
docker rmi devops-frontend:1.0 devops-orders:1.0 devops-users:1.0 devops-db:1.0
```
