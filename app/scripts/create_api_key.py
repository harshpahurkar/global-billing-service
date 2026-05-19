"""Create an API key. Run inside the container or against a configured DATABASE_URL.

Usage:
    python -m app.scripts.create_api_key "human-readable-name"

The plaintext key is printed once to stdout — only the SHA-256 hash is stored.
There is no way to recover the plaintext later; if it's lost, deactivate the row
and issue a new key.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.security import generate_api_key, hash_api_key  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.api_key import APIKey  # noqa: E402


def main(name: str) -> None:
    plain = generate_api_key()
    db = SessionLocal()
    try:
        db.add(APIKey(name=name, hashed_key=hash_api_key(plain), is_active=True))
        db.commit()
    finally:
        db.close()

    print(f"API key '{name}' created.")
    print(f"Key (shown once, store it now): {plain}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.create_api_key <name>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
