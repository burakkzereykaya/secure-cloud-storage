import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_dek() -> bytes:
    return os.urandom(32)


def encrypt_file(data: bytes, dek: bytes) -> tuple[bytes, bytes]:
    if not data:
        raise ValueError("File cannot be empty")
    if len(dek)!=32:
        raise ValueError("Decryption method requires 32 byte decryption")
    iv_or_nonce = os.urandom(12) #standart gcm size
    aesgcm = AESGCM(dek)
    encrypted_data = aesgcm.encrypt(iv_or_nonce, data,None)
    return encrypted_data, iv_or_nonce


def decrypt_file(encrypted_data: bytes, dek: bytes, iv_or_nonce: bytes) -> bytes:
    if not encrypted_data:
        raise ValueError("Encrypted data cannot be empty")
    if len(dek)!=32:
        raise ValueError("Decryption method requires 32 byte decryption")
    aesgcm = AESGCM(dek)
    decrypted_data = aesgcm.decrypt(iv_or_nonce, encrypted_data,None)
    return decrypted_data
