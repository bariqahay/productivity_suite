"""
One-time migration script: plain-text passwords in ADMIN_USERS → bcrypt hashes.

Usage:
    python migrate_passwords.py

What it does:
  1. Reads ADMIN_USERS from .env (format: user1:pass1,user2:pass2)
  2. Hashes every password with bcrypt (cost factor 12)
  3. Rewrites ADMIN_USERS in .env with hashed values
  4. Skips entries that are already bcrypt hashes (starts with $2b$)

Run this script ONCE after deploying this update.
"""

import os
import re
import sys

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt is not installed. Run: pip install bcrypt")
    sys.exit(1)

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


def is_bcrypt_hash(value: str) -> bool:
    """Return True if value already looks like a bcrypt hash."""
    return value.startswith(("$2b$", "$2a$", "$2y$"))


def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt (cost=12)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "utf-8"
    )


def migrate():
    if not os.path.isfile(ENV_FILE):
        print(f"ERROR: .env not found at {ENV_FILE}")
        sys.exit(1)

    with open(ENV_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Find the ADMIN_USERS line
    match = re.search(r"^(ADMIN_USERS\s*=\s*)(.+)$", content, flags=re.MULTILINE)
    if not match:
        print("ERROR: ADMIN_USERS key not found in .env")
        sys.exit(1)

    prefix = match.group(1)  # e.g. "ADMIN_USERS="
    raw_value = match.group(2).strip()

    pairs = []
    migrated = 0
    skipped = 0

    for entry in raw_value.split(","):
        entry = entry.strip()
        if ":" not in entry:
            print(f"  WARNING: skipping malformed entry: {entry!r}")
            continue

        username, password = entry.split(":", 1)
        username = username.strip()
        password = password.strip()

        if is_bcrypt_hash(password):
            print(f"  SKIP   {username}: already hashed")
            pairs.append(f"{username}:{password}")
            skipped += 1
        else:
            hashed = hash_password(password)
            print(f"  HASHED {username}: {password!r} → {hashed}")
            pairs.append(f"{username}:{hashed}")
            migrated += 1

    if migrated == 0:
        print("\nAll passwords are already hashed. Nothing to do.")
        return

    new_value = ",".join(pairs)
    new_content = content[: match.start()] + prefix + new_value + content[match.end() :]

    # Write back
    with open(ENV_FILE, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    print(f"\nDone. Migrated {migrated} password(s), skipped {skipped}.")
    print("Restart your Flask server so the new hashes take effect.")


if __name__ == "__main__":
    print(f"Migrating ADMIN_USERS passwords in: {ENV_FILE}\n")
    migrate()
