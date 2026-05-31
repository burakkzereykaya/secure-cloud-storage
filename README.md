# Secure Cloud Storage

## Project Description

Secure Cloud Storage is a FastAPI-based file storage application that encrypts files before storing them in Azure Blob Storage. It supports authenticated users, role-based admin access, file sharing, expiring download links, audit logging, and SHA-256 integrity checks.

The deployed backend is available at:

```text
https://secure-cloud-service-f5fdgremc5b9bvfe.polandcentral-01.azurewebsites.net
```

## Features

- JWT authentication
- Argon2 password hashing
- AES-GCM file encryption
- Azure Blob Storage
- Azure Key Vault-ready production secret management
- RBAC
- Audit logging
- SHA-256 integrity verification
- Authorized file sharing
- Expiring download links
- Admin users/files/logs dashboard
- GitHub Actions CI/CD deployment to Azure App Service

## Technology Stack

- Backend: Python, FastAPI, SQLAlchemy, Uvicorn
- Frontend: HTML, CSS, vanilla JavaScript
- Database: PostgreSQL in production, SQLite for automated tests
- Cloud: Azure App Service, Azure Blob Storage, Azure Database for PostgreSQL, Azure Key Vault
- Security: JWT, Argon2, AES-GCM, SHA-256, RBAC
- CI/CD: GitHub Actions

## System Architecture

```text
Browser frontend
  -> FastAPI backend on Azure App Service
  -> PostgreSQL metadata database
  -> Azure Blob Storage encrypted file objects
  -> Azure Key Vault / App Service settings for production secrets
```

Architecture and flow diagrams are stored in `docs/`.

## Security Mechanisms

- Passwords are hashed with Argon2 before storage.
- Login returns a signed JWT access token.
- Protected endpoints require a valid Bearer token.
- Uploaded files are encrypted with AES-GCM before Blob upload.
- The plaintext SHA-256 hash is stored and verified after decrypting downloads.
- Users can access only owned or shared files unless they are admins.
- Admin endpoints require the `admin` role.
- Upload, download, sharing, admin, integrity, and failure events are stored in audit logs.

## Installation Instructions

```powershell
git clone <repository-url>
cd secure-cloud-storage
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file in the project root. Do not commit it.

## Environment Variables

```text
DATABASE_URL=
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

AZURE_STORAGE_ACCOUNT=
AZURE_CONTAINER_NAME=
AZURE_STORAGE_CONNECTION_STRING=

AZURE_KEY_VAULT_URL=
```

For Azure PostgreSQL, `DATABASE_URL` should include SSL:

```text
postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

## Running the Backend

```powershell
.\.venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Running the Frontend

The backend serves the static frontend from `frontend/`, so the easiest local flow is:

```text
http://127.0.0.1:8000
```

To run it as a separate static site:

```powershell
python -m http.server 3000 -d frontend
```

Then open:

```text
http://127.0.0.1:3000
```

## Deployment Information

Backend target:

```text
FastAPI -> Azure App Service
```

Startup command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

CI/CD:

```text
GitHub Actions -> tests -> Azure App Service deploy
```

Production secrets are configured in Azure App Service Environment variables. The local `.env` file is ignored by Git.

## API Overview

- `POST /auth/register`
- `POST /auth/login`
- `GET /users/me`
- `POST /files/upload`
- `GET /files/my-files`
- `GET /files/shared-with-me`
- `GET /files/{file_id}`
- `GET /files/{file_id}/download`
- `POST /files/{file_id}/share`
- `DELETE /files/{file_id}/share`
- `DELETE /files/{file_id}/share/{user_id}`
- `POST /files/{file_id}/share-link`
- `GET /share/{token}/download`
- `GET /admin/users`
- `GET /admin/files`
- `GET /admin/logs`

## Testing Summary

Automated smoke tests cover:

- register/login/JWT validation
- upload/download encryption flow
- metadata view
- RBAC access checks
- file sharing and revoke
- expiring links
- admin access
- audit logs
- invalid uploads
- SHA-256 integrity failure

Run tests:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_week13_smoke -v
```

## Screenshots

Recommended screenshots for the final report:

- login/register screen
- user dashboard
- successful upload
- My Files table
- Shared With Me table
- expiring link creation
- admin users/files/logs tables
- Azure App Service overview
- Azure Blob container with `.enc` file
- PostgreSQL resource overview
- Key Vault overview

Do not show tokens, passwords, connection strings, storage keys, or secret values.

## Future Improvements

- Refresh tokens or shorter-lived sessions with silent renewal
- Dedicated migrations with Alembic
- Direct Azure Key Vault SDK integration for file key wrapping
- More admin filters and log export
- Separate Azure Static Web Apps frontend deployment
- End-to-end browser tests
