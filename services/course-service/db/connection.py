import os
import time

import mysql.connector
from mysql.connector import Error

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


def row_to_course(row):
    return row if row is not None else None


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


def create_course(title, description, duration, level, category):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO courses (title, description, duration, level, category)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (title, description, duration, level, category),
        )
        connection.commit()
        cursor.execute("SELECT * FROM courses WHERE id = %s", (cursor.lastrowid,))
        row = cursor.fetchone()
        return row_to_course(row)
    finally:
        connection.close()


def update_course(
    course_id,
    title=None,
    description=None,
    duration=None,
    level=None,
    category=None,
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
    if level is not None:
        updates.append("level = %s")
        values.append(level)
    if category is not None:
        updates.append("category = %s")
        values.append(category)
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


def create_enrollment(user_id, course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO enrollments (user_id, course_id)
            VALUES (%s, %s)
            """,
            (user_id, course_id),
        )
        connection.commit()
        cursor.execute("SELECT * FROM enrollments WHERE id = %s", (cursor.lastrowid,))
        return cursor.fetchone()
    finally:
        connection.close()


def delete_enrollment(user_id, course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM enrollments
            WHERE user_id = %s AND course_id = %s
            """,
            (user_id, course_id),
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


def get_enrollment(user_id, course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM enrollments
            WHERE user_id = %s AND course_id = %s
            """,
            (user_id, course_id),
        )
        return cursor.fetchone()
    finally:
        connection.close()


def get_enrollments_by_user(user_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT e.*, c.title, c.description, c.duration, c.level, c.category
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.user_id = %s
            ORDER BY e.enrolled_at DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def get_enrollments_by_course(course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT e.id, e.user_id, e.course_id, e.status,
                   e.enrolled_at, e.completed_at
            FROM enrollments e
            WHERE e.course_id = %s
            ORDER BY e.enrolled_at DESC
            """,
            (course_id,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def update_enrollment_status(enrollment_id, status):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            UPDATE enrollments
            SET status = %s,
                completed_at = CASE
                    WHEN %s = 'completed' THEN CURRENT_TIMESTAMP
                    WHEN %s != 'completed' THEN NULL
                    ELSE completed_at
                END
            WHERE id = %s
            """,
            (status, status, status, enrollment_id),
        )
        connection.commit()
        cursor.execute("SELECT * FROM enrollments WHERE id = %s", (enrollment_id,))
        return cursor.fetchone()
    finally:
        connection.close()
