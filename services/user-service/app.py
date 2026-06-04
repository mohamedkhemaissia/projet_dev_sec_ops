from flask import Flask
from routes.users import users_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(users_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
