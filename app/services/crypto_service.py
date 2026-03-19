import os


def generate_dek() -> bytes:
    return os.urandom(32)


def encrypt_file(file_bytes: bytes, dek: bytes) -> tuple[bytes, bytes]:
    iv_or_nonce = os.urandom(12)
    encrypted_data = file_bytes
    return encrypted_data, iv_or_nonce


def decrypt_file(encrypted_data: bytes, dek: bytes, iv_or_nonce: bytes) -> bytes:
    return encrypted_data