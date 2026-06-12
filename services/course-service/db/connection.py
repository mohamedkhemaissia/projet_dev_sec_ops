"""MySQL storage helpers for the Course Service."""

import os
import time

import mysql.connector
from mysql.connector import Error

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "tms_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "tms_password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "course_service_db")


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


def row_to_course(row):
    return row if row is not None else None


def init_db():
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                duration DOUBLE NOT NULL,
                instructor VARCHAR(255) NOT NULL
            )
            """)
        cursor.execute("SELECT COUNT(*) AS total FROM courses")
        total_courses = cursor.fetchone()["total"]
        if total_courses == 0:
            cursor.executemany(
                """
                INSERT INTO courses (title, description, duration, instructor)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (
                        "DevSecOps Fundamentals",
                        "Introduction to secure delivery pipelines",
                        24,
                        "Dr Martin",
                    ),
                    (
                        "Docker and CI/CD",
                        "Learn containers and automation basics",
                        18,
                        "Ms Sara",
                    ),
                ],
            )
        connection.commit()
    finally:
        connection.close()


def get_all_courses():
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM courses ORDER BY id ASC")
        rows = cursor.fetchall()
        return [row_to_course(row) for row in rows]
    finally:
        connection.close()


def get_course_by_id(course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
        row = cursor.fetchone()
        return row_to_course(row)
    finally:
        connection.close()


def create_course(title, description, duration, instructor):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO courses (title, description, duration, instructor)
            VALUES (%s, %s, %s, %s)
            """,
            (title, description, duration, instructor),
        )
        connection.commit()
        cursor.execute("SELECT * FROM courses WHERE id = %s", (cursor.lastrowid,))
        row = cursor.fetchone()
        return row_to_course(row)
    finally:
        connection.close()


def update_course(
    course_id, title=None, description=None, duration=None, instructor=None
):
    updates = []
    values = []

    if title is not None:
        updates.append("title = %s")
        values.append(title)
    if description is not None:
        updates.append("description = %s")
        values.append(description)
    if duration is not None:
        updates.append("duration = %s")
        values.append(duration)
    if instructor is not None:
        updates.append("instructor = %s")
        values.append(instructor)

    if not updates:
        return get_course_by_id(course_id)

    values.append(course_id)

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"UPDATE courses SET {', '.join(updates)} WHERE id = %s", values)
        connection.commit()
        cursor.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
        row = cursor.fetchone()
        return row_to_course(row)
    finally:
        connection.close()


def delete_course(course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


#init_db()
