"""User model helpers used by the Flask routes."""


def make_user(user_id, name, email, password_hash, role="learner"):
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "role": role,
    }


def public_user(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "learner"),
    }
