import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from routes.courses import courses_bp
from config import Config
from db.connection import init_db 

# Ensure local package modules are importable when running the service directly.
sys.path.insert(0, os.path.dirname(__file__))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/*": {"origins": "*"}})
    with app.app_context(): 
        init_db()
    app.register_blueprint(courses_bp)

    @app.errorhandler(400)
    def bad_request(error):
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": "The request could not be understood",
                }
            ),
            400,
        )

    @app.errorhandler(401)
    def unauthorized(error):
        return (
            jsonify({"error": "unauthorized", "message": "Authentication is required"}),
            401,
        )

    @app.errorhandler(403)
    def forbidden(error):
        return (
            jsonify(
                {
                    "error": "forbidden",
                    "message": "You are not allowed to access this resource",
                }
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "not_found", "message": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return (
            jsonify(
                {"error": "method_not_allowed", "message": "HTTP method not allowed"}
            ),
            405,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return (
            jsonify(
                {
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                }
            ),
            500,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=Config.DEBUG)