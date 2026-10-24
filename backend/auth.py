import hashlib
import hmac
import secrets

from database.db import get_db_connection


ITERATIONS = 310_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def admin_exists():
    conn = get_db_connection()
    try:
        return conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone() is not None
    finally:
        conn.close()


def create_account(username, password, role="user"):
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username tenke iha karakter 3 ka liu.")
    if len(password) < 8:
        raise ValueError("Password tenke iha karakter 8 ka liu.")
    if role not in ("admin", "user"):
        raise ValueError("Role la validu.")

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def authenticate(username, password):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT user_id, username, password_hash, role FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        if row and verify_password(password, row["password_hash"]):
            return {"user_id": row["user_id"], "username": row["username"], "role": row["role"]}
        return None
    finally:
        conn.close()


def get_account(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT user_id, username, role FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_password(user_id, password):
    if len(password) < 8:
        raise ValueError("Password tenke iha karakter 8 ka liu.")
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(password), user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
