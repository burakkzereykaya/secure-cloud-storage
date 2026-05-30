# Week 14 Deployment Checklist

## 1. Production environment variables

Do not upload the local `.env` file to GitHub. Add these values in Azure App Service > Settings > Environment variables:

```text
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
SECRET_KEY=<long-random-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=https://your-frontend-domain.example

AZURE_STORAGE_ACCOUNT=<storage-account-name>
AZURE_CONTAINER_NAME=<container-name>
AZURE_STORAGE_CONNECTION_STRING=<storage-connection-string>

AZURE_KEY_VAULT_URL=https://your-key-vault.vault.azure.net/
```

Keep local-only values in `.env`. The application reads real environment variables first, so Azure values override local `.env` values in production.

## 2. Backend deploy

Target:

```text
FastAPI -> Azure App Service
Runtime -> Python
```

Startup command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

If the Azure screen does not accept shell expansion, use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. Database live test

Use the deployed backend URL:

```text
POST https://your-backend-app.azurewebsites.net/auth/register
POST https://your-backend-app.azurewebsites.net/auth/login
GET  https://your-backend-app.azurewebsites.net/users/me
```

Common failure points:

- `DATABASE_URL` is wrong
- PostgreSQL firewall does not allow the App Service
- PostgreSQL requires `sslmode=require`
- username or password is wrong

## 4. Azure Blob live test

In the live frontend or API:

1. Register or login.
2. Upload a `.txt`, `.png`, `.jpg`, or `.pdf`.
3. Confirm Azure Portal > Storage Account > Container shows an `uploads/<user-id>/*.enc` blob.
4. Download the file from the app and verify the decrypted content opens correctly.
5. Download the blob directly from Azure Portal and verify it is encrypted/unreadable.

## 5. Key Vault test

If secrets are stored in Key Vault, prefer Azure App Service Key Vault references for environment variables. Then the app still reads normal variables such as `SECRET_KEY` and `AZURE_STORAGE_CONNECTION_STRING`, while Azure resolves them from Key Vault.

If direct Key Vault access is required:

1. Enable App Service Managed Identity.
2. Grant that identity permission to read secrets in Key Vault.
3. Confirm `AZURE_KEY_VAULT_URL` points to the vault URL.

## 6. Frontend deploy

Recommended Azure option:

```text
Azure Static Web Apps
App location: frontend
Output location: leave empty
```

Alternative easy options:

```text
Vercel
Netlify
App Service
```

## 7. Frontend API URL

Set the live backend URL in `frontend/config.js` before deploying the frontend:

```javascript
window.SCS_API_BASE = "https://your-backend-app.azurewebsites.net";
```

Users can still override this from the login screen API URL field. The value is saved in browser local storage.

## 8. CORS

Set `CORS_ORIGINS` on the backend App Service to the deployed frontend domain:

```text
CORS_ORIGINS=https://your-frontend-domain.example
```

For multiple domains, separate them with commas:

```text
CORS_ORIGINS=https://your-frontend-domain.example,https://your-backend-app.azurewebsites.net
```

## 9. Live demo test

Run this full flow on the deployed frontend:

1. Register
2. Login
3. Upload
4. Download
5. Metadata view
6. Share file
7. Shared with me
8. Expiring link
9. Admin panel
10. Logs
11. Logout
