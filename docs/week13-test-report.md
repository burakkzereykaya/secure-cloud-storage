# Week 13 Test Report

## Test Run

- Date: 2026-05-27
- Automated command:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_week13_smoke -v
```

- Result: PASS
- Automated tests run: 7
- Automated failures: 0

## Automated Test Coverage

| Area | Scenario | Expected | Status |
| --- | --- | --- | --- |
| Auth | Register creates active user | User saved in DB | PASS |
| Auth | Login returns JWT | `access_token` returned and decodes | PASS |
| Auth | Wrong password rejected | `401 Unauthorized` | PASS |
| Auth | Invalid token rejected | `401 Unauthorized` | PASS |
| Auth | Expired token rejected | `401 Unauthorized` | PASS |
| Auth | Inactive user rejected | `403 Forbidden` | PASS |
| Upload / Download | User uploads text file | Metadata saved and encrypted blob stored | PASS |
| Upload / Download | User downloads own file | Downloaded bytes match original | PASS |
| Upload / Download | Metadata endpoint returns file info | Correct file id returned | PASS |
| Encryption | Blob data is not plaintext | Stored blob differs from original bytes | PASS |
| Encryption | Two files use different DEK/nonce | Key, nonce, ciphertext differ | PASS |
| Encryption | Wrong key/nonce fails decrypt | Exception raised | PASS |
| RBAC | User sees only own files | Other user's list is empty | PASS |
| RBAC | User cannot download another user's file | `403 Forbidden` | PASS |
| RBAC | Admin can list all files | File appears in admin list | PASS |
| RBAC | Normal user cannot become admin | `403 Forbidden` | PASS |
| Logging | Upload logged | `UPLOAD_SUCCESS` exists | PASS |
| Logging | Download logged | `DOWNLOAD_SUCCESS` exists | PASS |
| Logging | Unauthorized access logged | `UNAUTHORIZED_ACCESS` exists | PASS |
| Logging | Admin activity logged | `ADMIN_VIEWED_FILES` exists | PASS |
| Logging | Share link activity logged | create/use/expired logs exist | PASS |
| Security | Invalid file type rejected | `400 Bad Request` | PASS |
| Security | Large file rejected | `413 Payload Too Large` | PASS |
| SHA-256 | Upload stores hash | DB hash equals plaintext hash | PASS |
| SHA-256 | Download verifies hash | `INTEGRITY_CHECK_SUCCESS` logged | PASS |
| SHA-256 | Tampered encrypted data blocked | `409 Conflict` | PASS |
| File sharing | Owner shares file with user | Permission row created | PASS |
| File sharing | Shared user sees shared file | File appears in shared list | PASS |
| File sharing | Shared user downloads file | Downloaded bytes match original | PASS |
| File sharing | Revoked share blocks access | `403 Forbidden` | PASS |
| Expiring link | Link created | Random token returned | PASS |
| Expiring link | Token download works | Downloaded bytes match original | PASS |
| Expiring link | Expired token rejected | `410 Gone` | PASS |
| Expiring link | Invalid token rejected | `404 Not Found` | PASS |

## Manual / Real Environment Tests

These should be checked with the real Azure PostgreSQL and Azure Blob configuration.

| Area | Scenario | Evidence | Status |
| --- | --- | --- | --- |
| Azure Blob | Uploaded blob exists in container | Confirmed in Azure container | PASS |
| Azure Blob | Blob content is encrypted / unreadable | Confirmed by downloading blob directly | PASS |
| Azure Blob | Manually modified blob blocks download | Screenshot: frontend/API `409` response | PASS |
| Rate limiting | Repeated login/upload requests are limited | Confirmed in Week 11 with `429` | PASS |
| Git hygiene | `.env` is not tracked by GitHub | Confirmed; add screenshot/evidence if needed | PASS |
| Frontend flow | Register -> Login -> Upload -> Metadata -> Download | Confirmed; screenshots can be added for report | PASS |
| Frontend flow | Share file -> Shared With Me -> Revoke | Confirmed by API/command flow; frontend screenshots can be added | PASS |
| Frontend flow | Create expiring link -> token download -> expired link | Confirmed | PASS |
| Admin panel | Users, files, logs visible for admin | Confirmed by endpoint/admin panel testing; screenshots can be added | PASS |
| Admin panel | Normal user cannot access admin endpoints | Confirmed with `403 Forbidden` | PASS |

## Frontend Demo Script

1. Open `http://127.0.0.1:8000`.
2. Register `user1@example.com`.
3. Login as `user1@example.com`.
4. Upload a `.txt`, `.png`, `.jpg`, or `.pdf` file.
5. Open My Files and verify the uploaded file appears.
6. Click Metadata and capture the metadata panel.
7. Download the file and verify it opens correctly.
8. Register or login as `user2@example.com`.
9. Login as `user1@example.com` again.
10. Share the file with `user2@example.com`.
11. Login as `user2@example.com`.
12. Open Shared With Me and download the shared file.
13. Login as `user1@example.com`.
14. Revoke the share using the displayed shared user id.
15. Login as `user2@example.com` and verify access is blocked.
16. Login as `user1@example.com`.
17. Create an expiring link.
18. Use the token link to download.
19. Wait until expiry and verify `410 Gone`.
20. Login as admin and capture Users, All Files, and Logs.
21. Logout.

## Notes

- Automated tests use SQLite and an in-memory fake Blob store for repeatability.
