from flask import Blueprint, jsonify, request, abort

users_bp = Blueprint('users', __name__, url_prefix='/users')

# simple in-memory storage (see db/connection.py)
from ..db.connection import users_storage


@users_bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


@users_bp.route('', methods=['GET'])
def get_users():
    return jsonify(users_storage['users']), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    for u in users_storage['users']:
        if u['id'] == user_id:
            return jsonify(u), 200
    abort(404)
