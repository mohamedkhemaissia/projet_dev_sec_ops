from flask import Flask
from routes.courses import courses_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(courses_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=True)
