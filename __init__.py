from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins import register_plugin_assets_directory
from .challenges import DockerChallengeType
from .routes import docker_bp
from flask import Flask

def load(app : Flask):
    CHALLENGE_CLASSES["docker"] = DockerChallengeType
    app.register_blueprint(docker_bp)
    register_plugin_assets_directory(app, base_path='/plugins/docker_challenges/templates/')

    app.db.create_all()
