def public_user(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "learner"),
        "avatar_url": user.get("avatar_url"),
    }
