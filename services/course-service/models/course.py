"""Course model (simple dict-based schema)."""

def make_course(course_id, title, description, duration):
    return {"id": course_id, "title": title, "description": description, "duration": duration}
