# Stage 1 Guide - Run Everything Locally (Without Docker)

## 1) Objective
Build and run one React frontend, two Flask microservices, and one shared PostgreSQL database fully on your local machine.

## 2) Why this concept exists
Running everything locally first helps you separate application problems from container and orchestration problems.

## 3) Production problem this solves
Teams reduce deployment failures by validating service boundaries, API contracts, and database schema before introducing Docker and Kubernetes.

## 4) How companies use it
Engineering teams implement a local-first workflow for fast debugging and reliable CI pipelines.

## 5) Interview expectations
You should explain why local validation is the first stage in a cloud-native delivery lifecycle.

## 6) Common mistakes
- Using embedded/local DB instead of shared external PostgreSQL
- Hardcoding service URLs and credentials
- Ignoring logs and error paths
- Skipping API validation between services

## 7) Troubleshooting techniques
- Check `/health` endpoint of each service
- Verify `DATABASE_URL` and service ports
- Inspect service logs for JSON error entries
- Call APIs directly with curl before opening frontend

## 8) Implementation steps
1. Install prerequisites:
   - Python 3.11+
   - Node.js 20+
   - PostgreSQL 15+
2. Create database:
   ```bash
   createdb devops_project
   psql devops_project -f /home/runner/work/Python-project/Python-project/database/init.sql
   ```
3. Create `.env` from `.env.example` and set valid values.
4. Create Python virtual environment and install users service dependencies:
   ```bash
   cd /home/runner/work/Python-project/Python-project
   python -m venv .venv
   source .venv/bin/activate
   pip install -r services/users_service/requirements.txt
   pip install -r services/orders_service/requirements.txt
   ```
5. Start users service:
   ```bash
   python /home/runner/work/Python-project/Python-project/services/users_service/app.py
   ```
6. Start orders service in another terminal:
   ```bash
   python /home/runner/work/Python-project/Python-project/services/orders_service/app.py
   ```
7. Start frontend:
   ```bash
   cd /home/runner/work/Python-project/Python-project/frontend
   npm install
   npm run dev
   ```

## 9) Every file explained
- `services/users_service/app.py`: user CRUD API with PostgreSQL access and structured logs.
- `services/orders_service/app.py`: order API, validates user existence by calling users service.
- `database/init.sql`: shared schema for users and orders tables.
- `frontend/src/*`: React UI to create/list users and orders through REST APIs.
- `.env.example`: central environment contract for all services.
- `scripts/start_stage1.sh`: optional helper to start both backend services.

## 10) Commands and flags explained
- `python -m venv .venv`: creates isolated Python environment.
- `pip install -r <file>`: installs exact dependencies from requirements file.
- `npm run dev`: runs Vite dev server with hot reload.
- `psql <db> -f <file>`: applies SQL schema file to PostgreSQL database.

## 11) How to verify success
- `GET http://localhost:5001/health` returns users-service ok.
- `GET http://localhost:5002/health` returns orders-service ok.
- Frontend opens on Vite URL and can create users/orders.

## 12) How to debug failures
- If users API fails, validate `DATABASE_URL` and schema migration status.
- If orders API fails, validate `USERS_SERVICE_URL` and users-service availability.
- If frontend fails, confirm `VITE_USERS_API_URL` and `VITE_ORDERS_API_URL` values.

## 13) Production best practices
- Keep environment variables outside source control.
- Keep services stateless.
- Return explicit error codes and machine-readable JSON errors.
- Use structured logs for central log aggregation.

## 14) Only then continue
After local validation is stable, move to Stage 2 (Dockerize each service individually).
