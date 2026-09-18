import os
import time

import mysql.connector
from mysql.connector import Error

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "tms_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "training_platform_db")

COURSE_SORT_EXPRESSIONS = {
    None: "c.id ASC",
    "popular": "enrollment_count DESC, c.id ASC",
    "recent": "c.created_at DESC, c.id ASC",
    "completion_rate": "completion_rate DESC, c.id ASC",
}

COURSE_STATS_SELECT = """
    SELECT c.*,
           COUNT(e.id) AS enrollment_count,
           COALESCE(SUM(CASE WHEN e.status = 'in_progress' THEN 1 ELSE 0 END), 0)
               AS in_progress_count,
           COALESCE(SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END), 0)
               AS completed_count,
           CASE
               WHEN COUNT(e.id) = 0 THEN 0
               ELSE 100.0 * SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END)
                    / COUNT(e.id)
           END AS completion_rate
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
"""

COURSE_GROUP_BY = """
    GROUP BY c.id, c.title, c.description, c.duration, c.level,
             c.category, c.created_at
"""

COURSE_RECOMMENDATION_QUERY = """
    SELECT c.*,
           COUNT(e.id) AS enrollment_count,
           COALESCE(SUM(CASE WHEN e.status = 'in_progress' THEN 1 ELSE 0 END), 0)
               AS in_progress_count,
           COALESCE(SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END), 0)
               AS completed_count,
           CASE
               WHEN COUNT(e.id) = 0 THEN 0
               ELSE 100.0 * SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END)
                    / COUNT(e.id)
           END AS completion_rate
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    WHERE NOT EXISTS (
        SELECT 1
        FROM enrollments learner_enrollment
        WHERE learner_enrollment.user_id = %s
          AND learner_enrollment.course_id = c.id
    )
    GROUP BY c.id, c.title, c.description, c.duration, c.level,
             c.category, c.created_at
"""


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
    if row is None:
        return None

    normalized = dict(row)
    for field in ("enrollment_count", "in_progress_count", "completed_count"):
        if field in normalized and normalized[field] is not None:
            normalized[field] = int(normalized[field])
    if "completion_rate" in normalized and normalized["completion_rate"] is not None:
        normalized["completion_rate"] = float(normalized["completion_rate"])
    return normalized


def get_all_courses(sort=None, category=None, level=None):
    sort_expression = COURSE_SORT_EXPRESSIONS.get(sort)
    if sort_expression is None:
        raise ValueError("Unsupported course sort")

    conditions = []
    parameters = []
    if category is not None:
        conditions.append("c.category = %s")
        parameters.append(category)
    if level is not None:
        conditions.append("c.level = %s")
        parameters.append(level)

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        query = COURSE_STATS_SELECT
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += COURSE_GROUP_BY
        query += f" ORDER BY {sort_expression}"
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()
        return [row_to_course(row) for row in rows]
    finally:
        connection.close()


def get_course_by_id(course_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            COURSE_STATS_SELECT + " WHERE c.id = %s" + COURSE_GROUP_BY,
            (course_id,),
        )
        row = cursor.fetchone()
        return row_to_course(row)
    finally:
        connection.close()


def get_recommendation_data(user_id):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            COURSE_RECOMMENDATION_QUERY,
            (user_id,),
        )
        candidates = [row_to_course(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT e.course_id, e.status, c.category, c.level
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.user_id = %s
            ORDER BY e.course_id ASC
            """,
            (user_id,),
        )
        history = cursor.fetchall()
        return candidates, history
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
    if all(value is None for value in (title, description, duration, level, category)):
        return get_course_by_id(course_id)

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            UPDATE courses
            SET title = COALESCE(%s, title),
                description = COALESCE(%s, description),
                duration = COALESCE(%s, duration),
                level = COALESCE(%s, level),
                category = COALESCE(%s, category)
            WHERE id = %s
            """,
            (title, description, duration, level, category, course_id),
        )
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
                   e.enrolled_at, e.completed_at,
                   u.name AS learner_name, u.email AS learner_email
            FROM enrollments e
            JOIN users u ON u.id = e.user_id
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
