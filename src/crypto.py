"""
Encryption and password hashing for StackScreener.

API key encryption:
  - Fernet symmetric encryption (cryptography library)
  - Master key stored in the OS keyring — never on disk, never in source
    Windows  → Windows Credential Manager
    macOS    → macOS Keychain
    Linux    → SecretService (GNOME Keyring / KWallet)
  - On first call, a random key is generated and stored in the keyring

Password hashing:
  - PBKDF2-HMAC-SHA256 with a random per-user salt (stdlib only)
  - 260,000 iterations (OWASP 2023 recommendation)
"""

import hashlib
import secrets

import keyring
from cryptography.fernet import Fernet

_KEYRING_SERVICE = "StackScreener"
_KEYRING_ACCOUNT = "fernet_master_key"
_PBKDF2_ITERATIONS = 260_000


# ── Fernet key management ──────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    raw = keyring.get_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT)
    if raw is None:
        raw = Fernet.generate_key().decode()
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT, raw)
    return Fernet(raw.encode() if isinstance(raw, str) else raw)


# ── API key encryption ─────────────────────────────────────────────────────────

def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ── Password hashing ───────────────────────────────────────────────────────────

def hash_password(password: str) -> tuple[str, str]:
    """Hash a password. Returns (hash_hex, salt_hex)."""
    salt = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(candidate, stored_hash)
