from flask import Blueprint, jsonify, request, abort

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

from ..db.connection import courses_storage


@courses_bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


@courses_bp.route('', methods=['GET'])
def get_courses():
    return jsonify(courses_storage['courses']), 200


@courses_bp.route('/<int:course_id>', methods=['GET'])
def get_course(course_id):
    for c in courses_storage['courses']:
        if c['id'] == course_id:
            return jsonify(c), 200
    abort(404)
