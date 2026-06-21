from passlib.context import CryptContext
import secrets
import hashlib
import base64

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_secret(secret: str) -> str:
    return pwd_context.hash(secret)


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    try:
        return pwd_context.verify(plain_secret, hashed_secret)
    except Exception:
        return False


def generate_api_key() -> str:
    prefix = "ak"
    random_part = secrets.token_urlsafe(24)
    return f"{prefix}_{random_part}"


def generate_api_secret() -> str:
    return secrets.token_urlsafe(48)


def fingerprint_secret(secret: str) -> str:
    return base64.b64encode(
        hashlib.sha256(secret.encode("utf-8")).digest()
    ).decode("ascii")[:16]
