import hashlib
import hmac
import os
import secrets
from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.getenv("APP_ENCRYPTION_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        os.environ["APP_ENCRYPTION_KEY"] = key
    return Fernet(key.encode())


def encrypt_payload(payload: str) -> str:
    return _fernet().encrypt(payload.encode()).decode()


def decrypt_payload(payload: str) -> str:
    try:
        return _fernet().decrypt(payload.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt draft") from exc


def hash_secret(secret: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


def verify_secret(secret: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def admin_token_valid(value: str | None) -> bool:
    expected = os.getenv("ADMIN_TOKEN", "dev-admin-token")
    return bool(value) and secrets.compare_digest(value, expected)
