#!/usr/bin/env python3
"""
MapGen — Flask application entry point.

Serves the React frontend and API routes for poster generation.
"""

import matplotlib
matplotlib.use("Agg")

from flask import Flask, send_from_directory
from flask_cors import CORS

from api.routes import api


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="frontend/dist",
        static_url_path="",
    )
    CORS(app)
    app.register_blueprint(api)

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:path>")
    def catch_all(path):
        """Serve React SPA — all non-API routes go to index.html."""
        try:
            return send_from_directory(app.static_folder, path)
        except Exception:
            return send_from_directory(app.static_folder, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
