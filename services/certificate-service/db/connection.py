import os
import time
from uuid import uuid4

import mysql.connector
from mysql.connector import Error, IntegrityError

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "tms_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "tms_password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "training_platform_db")


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


def ensure_certificates_schema():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS certificates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                course_id INT NOT NULL,
                certificate_code VARCHAR(100) NOT NULL UNIQUE,
                status ENUM('active', 'revoked') NOT NULL DEFAULT 'active',
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_course_certificate (user_id, course_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def generate_certificate_code():
    return f"TH-{uuid4().hex[:12].upper()}"


def get_completed_enrollment(user_id, course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT e.*, c.title AS course_title, c.category, c.level
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.user_id = %s
              AND e.course_id = %s
              AND e.status = 'completed'
            """,
            (user_id, course_id),
        )
        return cursor.fetchone()
    finally:
        connection.close()


def get_certificate_by_user_and_course(user_id, course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT cert.*, u.name AS learner_name, u.email AS learner_email,
                   c.title AS course_title, c.category, c.level
            FROM certificates cert
            JOIN users u ON u.id = cert.user_id
            JOIN courses c ON c.id = cert.course_id
            WHERE cert.user_id = %s AND cert.course_id = %s
            """,
            (user_id, course_id),
        )
        return cursor.fetchone()
    finally:
        connection.close()


def get_certificate_by_id(certificate_id, user_id=None):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT cert.*, u.name AS learner_name, u.email AS learner_email,
                   c.title AS course_title, c.category, c.level
            FROM certificates cert
            JOIN users u ON u.id = cert.user_id
            JOIN courses c ON c.id = cert.course_id
            WHERE cert.id = %s
        """
        values = [certificate_id]
        if user_id is not None:
            query += " AND cert.user_id = %s"
            values.append(user_id)
        cursor.execute(query, values)
        return cursor.fetchone()
    finally:
        connection.close()


def get_certificates_by_user(user_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT cert.*, c.title AS course_title, c.category, c.level
            FROM certificates cert
            JOIN courses c ON c.id = cert.course_id
            WHERE cert.user_id = %s
            ORDER BY cert.issued_at DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def create_certificate(user_id, course_id):
    existing = get_certificate_by_user_and_course(user_id, course_id)
    if existing:
        return existing, False

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        for _ in range(3):
            code = generate_certificate_code()
            try:
                cursor.execute(
                    """
                    INSERT INTO certificates (user_id, course_id, certificate_code)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, course_id, code),
                )
                connection.commit()
                certificate_id = cursor.lastrowid
                return get_certificate_by_id(certificate_id), True
            except IntegrityError:
                connection.rollback()
        raise RuntimeError("Unable to generate a unique certificate code")
    finally:
        connection.close()


def verify_certificate(certificate_code):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT cert.id, cert.certificate_code, cert.status, cert.issued_at,
                   u.name AS learner_name,
                   c.title AS course_title, c.category, c.level
            FROM certificates cert
            JOIN users u ON u.id = cert.user_id
            JOIN courses c ON c.id = cert.course_id
            WHERE cert.certificate_code = %s
            """,
            (certificate_code,),
        )
        return cursor.fetchone()
    finally:
        connection.close()
