import asyncio
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{(Path(tempfile.gettempdir()) / f'scs_week13_{uuid.uuid4().hex}.db').as_posix()}"
os.environ.setdefault("AZURE_STORAGE_ACCOUNT", "test")
os.environ.setdefault("AZURE_CONTAINER_NAME", "test")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("AZURE_KEY_VAULT_URL", "https://test.vault.azure.net/")
os.environ.setdefault("SECRET_KEY", "week13-test-secret")

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from jose import jwt
from starlette.requests import Request

from app.api.routes import admin as admin_routes
from app.api.routes import files as file_routes
from app.core.dependencies import get_current_admin, get_current_user
from app.core.security import ALGORITHM, SECRET_KEY, create_access_token, decode_access_token
from app.db.base import Base
from app.db.models.access_log import AccessLog
from app.db.models.file import File
from app.db.models.share_link import ShareLink
from app.db.models.user import User
from app.db.session import SessionLocal, engine
from app.schemas.file import RevokeShareRequest, ShareFileRequest, ShareLinkCreateRequest
from app.services.auth_service import login_user, register_user
from app.services.crypto_service import decrypt_file
from app.services.hash_service import calculate_sha256


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self, size: int = -1) -> bytes:
        return self._data


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("testclient", 12345),
        }
    )


class Week13SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob_store: dict[str, bytes] = {}
        cls.original_upload = file_routes.upload_encrypted_file
        cls.original_download = file_routes.download_encrypted_file

        def fake_upload(data: bytes, blob_path: str) -> str:
            cls.blob_store[blob_path] = data
            return blob_path

        def fake_download(blob_path: str) -> bytes:
            return cls.blob_store[blob_path]

        file_routes.upload_encrypted_file = fake_upload
        file_routes.download_encrypted_file = fake_download

    @classmethod
    def tearDownClass(cls):
        file_routes.upload_encrypted_file = cls.original_upload
        file_routes.download_encrypted_file = cls.original_download
        engine.dispose()
        db_path = os.environ["DATABASE_URL"].replace("sqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.blob_store.clear()
        self.db = SessionLocal()
        self.request = make_request()

    def tearDown(self):
        self.db.close()

    def create_user(self, email: str, password: str = "Passw0rd!", role: str = "user") -> User:
        user = register_user(self.db, email, password)
        if role != "user":
            user.role = role
            self.db.commit()
            self.db.refresh(user)
        return user

    def upload_text_file(self, user: User, data: bytes = b"hello secure world") -> File:
        upload = asyncio.run(
            file_routes.upload_file(
                self.request,
                FakeUploadFile("hello.txt", "text/plain", data),
                self.db,
                user,
            )
        )
        return self.db.get(File, upload.id)

    def assert_http_error(self, status_code: int, func, *args, **kwargs):
        with self.assertRaises(HTTPException) as context:
            func(*args, **kwargs)
        self.assertEqual(context.exception.status_code, status_code)

    def assert_log_exists(self, action: str, status: str | None = None):
        query = self.db.query(AccessLog).filter(AccessLog.action == action)
        if status:
            query = query.filter(AccessLog.status == status)
        self.assertIsNotNone(query.first(), f"Missing log action={action} status={status}")

    def test_auth_register_login_jwt_and_rejections(self):
        user = self.create_user("user1@example.com")

        token_response = login_user(self.db, "user1@example.com", "Passw0rd!")
        self.assertEqual(token_response["token_type"], "bearer")
        payload = decode_access_token(token_response["access_token"])
        self.assertEqual(payload["sub"], str(user.id))

        current_user = get_current_user(self.request, token_response["access_token"], self.db)
        self.assertEqual(current_user.email, "user1@example.com")

        self.assert_http_error(401, login_user, self.db, "user1@example.com", "wrong-password")
        self.assert_http_error(401, get_current_user, self.request, "not-a-token", self.db)

        expired_token = jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        self.assert_http_error(401, get_current_user, self.request, expired_token, self.db)

        user.is_active = False
        self.db.commit()
        inactive_token = create_access_token(
            {"sub": str(user.id), "email": user.email, "role": user.role}
        )
        self.assert_http_error(403, get_current_user, self.request, inactive_token, self.db)

    def test_upload_download_metadata_encryption_and_integrity(self):
        user = self.create_user("owner@example.com")
        plaintext = b"plain text report"
        file_record = self.upload_text_file(user, plaintext)

        self.assertEqual(file_record.sha256_hash, calculate_sha256(plaintext))
        self.assertEqual(file_record.size, len(plaintext))
        self.assertIn(file_record.blob_path, self.blob_store)
        self.assertNotEqual(self.blob_store[file_record.blob_path], plaintext)

        response = file_routes.download_file(self.request, file_record.id, self.db, user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, plaintext)

        metadata = file_routes.get_file_detail(self.request, file_record.id, self.db, user)
        self.assertEqual(metadata.id, file_record.id)

        self.assert_log_exists("UPLOAD_SUCCESS", "success")
        self.assert_log_exists("INTEGRITY_CHECK_SUCCESS", "success")
        self.assert_log_exists("DOWNLOAD_SUCCESS", "success")
        self.assert_log_exists("METADATA_VIEWED", "success")

    def test_encryption_uses_unique_key_nonce_and_wrong_values_fail(self):
        user = self.create_user("owner@example.com")
        first = self.upload_text_file(user, b"same contents")
        second = self.upload_text_file(user, b"same contents")

        self.assertNotEqual(bytes(first.encrypted_dek), bytes(second.encrypted_dek))
        self.assertNotEqual(bytes(first.iv_or_nonce), bytes(second.iv_or_nonce))
        self.assertNotEqual(self.blob_store[first.blob_path], self.blob_store[second.blob_path])

        encrypted = self.blob_store[first.blob_path]
        wrong_key = bytes(second.encrypted_dek)
        wrong_nonce = bytes(second.iv_or_nonce)
        with self.assertRaises(Exception):
            decrypt_file(encrypted, wrong_key, bytes(first.iv_or_nonce))
        with self.assertRaises(Exception):
            decrypt_file(encrypted, bytes(first.encrypted_dek), wrong_nonce)

    def test_rbac_owner_shared_user_admin_and_unauthorized_logging(self):
        owner = self.create_user("owner@example.com")
        other = self.create_user("other@example.com")
        admin = self.create_user("admin@example.com", role="admin")
        file_record = self.upload_text_file(owner)

        self.assertEqual(file_routes.list_my_files(self.db, owner)[0].id, file_record.id)
        self.assertEqual(file_routes.list_my_files(self.db, other), [])
        self.assert_http_error(403, file_routes.download_file, self.request, file_record.id, self.db, other)
        self.assert_log_exists("UNAUTHORIZED_ACCESS", "forbidden")

        all_files = admin_routes.get_all_files(self.request, self.db, admin)
        self.assertEqual([item.id for item in all_files], [file_record.id])
        self.assert_http_error(403, get_current_admin, self.request, other, self.db)
        self.assertEqual(get_current_admin(self.request, admin, self.db).id, admin.id)
        self.assert_log_exists("ADMIN_VIEWED_FILES", "success")

    def test_file_sharing_and_revocation(self):
        owner = self.create_user("owner@example.com")
        shared_user = self.create_user("shared@example.com")
        file_record = self.upload_text_file(owner)

        permission = file_routes.share_file(
            self.request,
            file_record.id,
            ShareFileRequest(shared_with_email=shared_user.email, permission_type="read"),
            self.db,
            owner,
        )
        self.assertEqual(permission.shared_with_user_id, shared_user.id)

        shared_files = file_routes.list_shared_with_me(self.db, shared_user)
        self.assertEqual([item.id for item in shared_files], [file_record.id])
        response = file_routes.download_file(self.request, file_record.id, self.db, shared_user)
        self.assertEqual(response.body, b"hello secure world")

        result = file_routes.revoke_file_share_by_email(
            self.request,
            file_record.id,
            RevokeShareRequest(shared_with_email=shared_user.email),
            self.db,
            owner,
        )
        self.assertEqual(result["message"], "File share revoked")
        self.assert_http_error(
            403,
            file_routes.download_file,
            self.request,
            file_record.id,
            self.db,
            shared_user,
        )

        self.assert_log_exists("FILE_SHARED", "success")
        self.assert_log_exists("FILE_SHARE_REVOKED", "success")

    def test_expiring_link_valid_expired_invalid_and_logging(self):
        owner = self.create_user("owner@example.com")
        file_record = self.upload_text_file(owner)

        link = file_routes.create_share_link(
            self.request,
            file_record.id,
            ShareLinkCreateRequest(expires_in_minutes=60),
            self.db,
            owner,
        )
        self.assertTrue(link.token)

        response = file_routes.download_file_with_share_link(self.request, link.token, self.db)
        self.assertEqual(response.body, b"hello secure world")

        share_link = self.db.query(ShareLink).filter(ShareLink.token == link.token).first()
        share_link.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()
        self.assert_http_error(
            410,
            file_routes.download_file_with_share_link,
            self.request,
            link.token,
            self.db,
        )
        self.assert_http_error(
            404,
            file_routes.download_file_with_share_link,
            self.request,
            "invalid-token",
            self.db,
        )

        self.assert_log_exists("SHARE_LINK_CREATED", "success")
        self.assert_log_exists("SHARE_LINK_USED", "success")
        self.assert_log_exists("SHARE_LINK_EXPIRED", "failure")

    def test_security_rejections_and_hash_tamper_block_download(self):
        owner = self.create_user("owner@example.com")

        self.assert_http_error(
            400,
            lambda: asyncio.run(
                file_routes.upload_file(
                    self.request,
                    FakeUploadFile("malware.exe", "application/x-msdownload", b"x"),
                    self.db,
                    owner,
                )
            ),
        )
        self.assert_log_exists("INVALID_FILE_TYPE", "failure")

        self.assert_http_error(
            413,
            lambda: asyncio.run(
                file_routes.upload_file(
                    self.request,
                    FakeUploadFile(
                        "big.txt",
                        "text/plain",
                        b"x" * (file_routes.MAX_FILE_SIZE + 1),
                    ),
                    self.db,
                    owner,
                )
            ),
        )
        self.assert_log_exists("FILE_TOO_LARGE", "failure")

        file_record = self.upload_text_file(owner, b"original contents")
        tampered_ciphertext = AESGCM(bytes(file_record.encrypted_dek)).encrypt(
            bytes(file_record.iv_or_nonce),
            b"changed contents",
            None,
        )
        self.blob_store[file_record.blob_path] = tampered_ciphertext
        self.assert_http_error(
            409,
            file_routes.download_file,
            self.request,
            file_record.id,
            self.db,
            owner,
        )
        self.assert_log_exists("INTEGRITY_CHECK_FAILED", "failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)
