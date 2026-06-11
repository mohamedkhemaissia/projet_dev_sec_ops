"""MySQL storage helpers for the User Service."""

import os
import time

import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "tms_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "tms_password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "user_service_db")

DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@training.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin123!")


def get_connection():
    last_error = None
    for _ in range(30):
        try:
            return mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
                autocommit=False,
            )
        except Error as error:
            last_error = error
            time.sleep(2)
    raise last_error


def row_to_user(row):
    return row if row is not None else None


def init_db():
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user'
            )
            """)
        cursor.execute("SELECT COUNT(*) AS total FROM users")
        total_users = cursor.fetchone()["total"]
        if total_users == 0:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    "Admin",
                    DEFAULT_ADMIN_EMAIL,
                    generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                    "admin",
                ),
            )
        connection.commit()
    finally:
        connection.close()


def get_all_users():
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users ORDER BY id ASC")
        rows = cursor.fetchall()
        return [row_to_user(row) for row in rows]
    finally:
        connection.close()


def get_user_by_id(user_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        connection.close()


def create_user(name, email, password_hash, role="user"):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, password_hash, role),
        )
        connection.commit()
        cursor.execute("SELECT * FROM users WHERE id = %s", (cursor.lastrowid,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        connection.close()


def update_user(user_id, name=None, email=None, password_hash=None, role=None):
    updates = []
    values = []

    if name is not None:
        updates.append("name = %s")
        values.append(name)
    if email is not None:
        updates.append("email = %s")
        values.append(email)
    if password_hash is not None:
        updates.append("password_hash = %s")
        values.append(password_hash)
    if role is not None:
        updates.append("role = %s")
        values.append(role)

    if not updates:
        return get_user_by_id(user_id)

    values.append(user_id)

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", values)
        connection.commit()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return row_to_user(row)
    finally:
        connection.close()


def delete_user(user_id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


# init_db()
