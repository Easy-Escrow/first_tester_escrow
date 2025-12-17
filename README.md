# Escrow Starter (Django + React/Vite)

A ready-to-extend starter that wires a Django REST API (JWT, DRF, CORS, custom email user) to a React/Vite frontend. Includes Docker and local run instructions plus health indicators and request logging on both sides.

## Project structure
- `backend/` — Django project with REST framework, JWT auth, custom email-based user model, and health endpoint.
- `frontend/` — React + Vite app with login/register/dashboard screens and API status indicator.
- `docker-compose.yml` — run both services together for quick starts.

## Quickstart (Docker)
1. Copy environment defaults and adjust as needed:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Build and start both services:
   ```bash
   docker-compose up --build
   ```
3. Access the frontend at http://localhost:5173 (API served from http://localhost:8000).

## Backend (Django)
1. Install dependencies (inside a virtualenv recommended):
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Environment: duplicate `.env.example` and update secrets/hosts.
   ```bash
   cp backend/.env.example backend/.env
   ```
3. Apply migrations and run the server:
   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

### Key endpoints
- `POST /api/auth/register/` — email/password registration.
- `POST /api/auth/login/` — obtain JWT access/refresh tokens using email.
- `GET /api/auth/profile/` — authenticated profile retrieval.
- `GET /api/health/` — health check used by the frontend indicator.

### Logging
- Requests are logged via `config.middleware.RequestLogMiddleware` to the `api` logger.
- Health, login, and registration events emit console logs; configure logging output in `LOGGING` within `config/settings.py`.

## Frontend (React/Vite)
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Create an environment file:
   ```bash
   cp .env.example .env
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```

### Features
- Dark blue + white palette with Times New Roman typography.
- Login and registration forms talking to the Django API; JWT tokens stored locally.
- Dashboard displaying profile data.
- Top bar indicator polling `/api/health/` to show API availability on every screen.
- Axios interceptors log all requests/responses/errors to the console.

## Configuration notes
- CORS defaults to `http://localhost:5173`; adjust `CORS_ALLOWED_ORIGINS` in `backend/.env` for other hosts.
- The Django project ships with an initial migration for the custom user model (`accounts.User`).
- Update `ALLOWED_HOSTS` for deployment and replace `DJANGO_SECRET_KEY` in production.

## Testing the flow quickly
1. Register a user via the frontend or by cURL:
   ```bash
   curl -X POST http://localhost:8000/api/auth/register/ \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@example.com","password":"ChangeMe123"}'
   ```
2. Log in to obtain tokens:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@example.com","password":"ChangeMe123"}'
   ```
3. Use the access token for authenticated calls:
   ```bash
   curl http://localhost:8000/api/auth/profile/ -H "Authorization: Bearer <access>"
   ```

You're ready to extend business logic or UI features from here.
