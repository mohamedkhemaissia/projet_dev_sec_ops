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
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "training_platform_db")

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


def ensure_default_admin():
    admin = get_user_by_email(DEFAULT_ADMIN_EMAIL)
    if admin:
        update_user(
            admin["id"],
            password_hash=generate_password_hash(DEFAULT_ADMIN_PASSWORD),
            role="admin",
        )
        return

    create_user(
        "TrainingHub Admin",
        DEFAULT_ADMIN_EMAIL,
        generate_password_hash(DEFAULT_ADMIN_PASSWORD),
        "admin",
    )


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


def create_user(name, email, password_hash, role="learner"):
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


def update_user(
    user_id,
    name=None,
    email=None,
    password_hash=None,
    role=None,
):
    if all(value is None for value in (name, email, password_hash, role)):
        return get_user_by_id(user_id)

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            UPDATE users
            SET name = COALESCE(%s, name),
                email = COALESCE(%s, email),
                password_hash = COALESCE(%s, password_hash),
                role = COALESCE(%s, role)
            WHERE id = %s
            """,
            (name, email, password_hash, role, user_id),
        )
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
