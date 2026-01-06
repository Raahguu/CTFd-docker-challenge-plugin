import os

from flask import Flask

from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES

from .challenges import DockerChallengeType
from .container_controlers import start_cleaner
from .routes import docker_bp


def load(app: Flask):
    CHALLENGE_CLASSES["docker"] = DockerChallengeType
    app.register_blueprint(docker_bp)
    register_plugin_assets_directory(
        app, base_path="/plugins/docker_challenges/templates/"
    )

    app.db.create_all()

    if os.environ.get("GUNICORN_WORKER_ID") in (None, "0"):
        start_cleaner(app)
