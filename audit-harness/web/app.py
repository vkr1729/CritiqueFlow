import os
from flask import Flask
from web.routes import bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.urandom(24)
    app.register_blueprint(bp)
    return app
