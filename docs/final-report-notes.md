# Final Report Notes

## Technologies

- Python, FastAPI, Uvicorn
- SQLAlchemy ORM
- PostgreSQL production database
- SQLite test database
- Azure App Service
- Azure Blob Storage
- Azure Key Vault / App Service secret references
- HTML, CSS, vanilla JavaScript frontend
- GitHub Actions CI/CD

## Azure Services

- Azure App Service: hosts the FastAPI backend and static frontend.
- Azure Database for PostgreSQL: stores users, metadata, sharing permissions, expiring links, and logs.
- Azure Blob Storage: stores encrypted `.enc` file objects.
- Azure Key Vault: stores or references production secrets where configured.

## Database Tables

- `users`: account identity, password hash, role, active flag.
- `files`: metadata, blob path, SHA-256 hash, encrypted DEK, nonce, owner.
- `file_permissions`: active user-to-file sharing permissions.
- `share_links`: expiring anonymous download tokens.
- `access_logs`: audit trail for auth, file, sharing, admin, and failure events.

## API Endpoint List

- Auth: `POST /auth/register`, `POST /auth/login`
- User: `GET /users/me`
- Files: `POST /files/upload`, `GET /files/my-files`, `GET /files/shared-with-me`
- File detail/download: `GET /files/{file_id}`, `GET /files/{file_id}/download`
- Sharing: `POST /files/{file_id}/share`, `DELETE /files/{file_id}/share`
- Legacy revoke: `DELETE /files/{file_id}/share/{user_id}`
- Expiring links: `POST /files/{file_id}/share-link`, `GET /share/{token}/download`
- Admin: `GET /admin/users`, `GET /admin/files`, `GET /admin/logs`

## Encryption Flow

1. User uploads an allowed file.
2. Backend reads the plaintext bytes and calculates SHA-256.
3. Backend creates a random 256-bit data encryption key.
4. File bytes are encrypted with AES-GCM and a random nonce.
5. Encrypted bytes are uploaded to Azure Blob Storage as `.enc`.
6. File metadata, hash, key bytes, and nonce are stored in PostgreSQL.
7. On download, the encrypted blob is fetched, decrypted, and verified against the stored SHA-256 hash.

## Authentication Flow

1. User registers with email and password.
2. Password is hashed with Argon2.
3. User logs in with email/password.
4. Backend returns a JWT bearer token.
5. Protected endpoints validate the JWT and load the current user.
6. Expired or invalid tokens return `401`.

## RBAC Logic

- Normal users can access their own files.
- Normal users can access files shared with them through active permissions.
- Admin users can access admin-only endpoints and list users, files, and logs.
- File owner or admin can share and revoke file access.

## Logging Logic

Audit logs are created for:

- successful and failed login attempts
- uploads and downloads
- metadata views
- unauthorized access
- file sharing and revoke
- expiring link creation/use/expiry
- admin list actions
- integrity check success/failure
- rate limit events

## File Sharing Logic

1. Owner selects a file and enters another user's email.
2. Backend resolves the email to a user id.
3. An active `file_permissions` row is created.
4. Shared user sees the file in Shared With Me.
5. Owner can revoke access by entering the shared user's email.

## Expiring Link Logic

1. Owner creates a link with a lifetime in minutes.
2. Backend generates a random token and stores `expires_at`.
3. Anyone with the link can download until expiry.
4. Expired links are deactivated and return `410 Gone`.

## Test Results

Latest local smoke test:

```text
python -m unittest tests.test_week13_smoke -v
Ran 7 tests
OK
```

Live checks completed:

- register/login
- upload to Azure Blob
- download/decrypt
- metadata view
- share and revoke
- Shared With Me download
- expiring link
- admin users/files/logs
- logout

## Deployment URL

```text
https://secure-cloud-service-f5fdgremc5b9bvfe.polandcentral-01.azurewebsites.net
```

## Notes For Screenshots

Before capturing screenshots, hide or crop:

- JWT tokens
- passwords
- connection strings
- storage keys
- Key Vault secret values
- database passwords
