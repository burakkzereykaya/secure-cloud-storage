# Demo Scenario

## Prepared Users

Use non-personal demo accounts:

```text
admin@example.com -> admin
user1@example.com -> user
user2@example.com -> user
```

Registration creates normal users. If `admin@example.com` is not already admin, update its role in PostgreSQL before the demo:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

## Suggested Demo Flow

1. Login as `user1@example.com`.
2. Upload `test-document.txt` or another small sample file.
3. Show the file in My Files.
4. Open metadata for the uploaded file.
5. Download the file and verify it opens correctly.
6. Share the file with `user2@example.com`.
7. Logout and login as `user2@example.com`.
8. Open Shared With Me and download the shared file.
9. Logout and login as `user1@example.com`.
10. Create an expiring download link for the file.
11. Open the link and confirm it downloads.
12. Revoke `user2@example.com` access using the email field.
13. Login as `admin@example.com`.
14. Show Users, All Files, and Access Logs.
15. Open Azure Blob Storage and show the encrypted `.enc` blob.

## Demo Files

Use only safe sample files:

```text
sample-report.pdf
sample-image.png
test-document.txt
```

Do not upload real personal documents.

## Optional Failure Checks

- Try uploading an unsupported file type to show invalid upload handling.
- Try accessing a file as an unauthorized user.
- Open an expired link and show the expired link message.
- If prepared safely, tamper with an encrypted blob and show integrity failure.
