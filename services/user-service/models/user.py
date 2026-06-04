"""User model (simple dict-based schema)."""

def make_user(user_id, name, email):
    return {"id": user_id, "name": name, "email": email}
