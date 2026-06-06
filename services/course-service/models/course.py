"""Course model helpers used by the Flask routes."""


def make_course(course_id, title, description, duration, instructor):
    return {
        "id": course_id,
        "title": title,
        "description": description,
        "duration": duration,
        "instructor": instructor,
    }
