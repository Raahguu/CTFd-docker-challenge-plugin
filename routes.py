import subprocess
import json
from flask import Blueprint, jsonify
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user
from .models import UserContainer, DockerChallenge
from CTFd.models import db

docker_bp = Blueprint("docker", __name__)

def docker_query(path : str, method : str = "GET", body = ""):
    assert path.count(' ') == 0

    command = f'curl --unix-socket=/var/run/docker.sock http://v1.52/{path}'.split(' ')
    if method.upper() == "POST":
        command += [f'-H "Content-Type: application/json" -X {method} -d {body}']

    result = subprocess.run(command, stdout=subprocess.PIPE)

    if (result.stderr != ""):
        raise AssertionError(result.stderr)


    data = json.loads(result.stdout)
    try:
        if (data["message"] == ""): raise ZeroDivisionError
        raise ValueError(data["message"])
    except ZeroDivisionError: pass

    return data


@docker_bp.route("/docker/spawn/<int:challenge_id>", methods=["POST"])
@authed_only
def spawn_container(challenge_id):
    user = get_current_user()
    challenge = DockerChallenge.query.get_or_404(challenge_id)

    existing = UserContainer.query.filter_by(
        user_id=user.id, challenge_id=challenge.id
    ).first()
    if existing:
        return jsonify({"ip": existing.ip})

    # Create the container
    data = f'"Image": "{challenge.image}"'
    container_id = docker_query("/containers/create", "POST", data)["Id"]

    # Start the container
    docker_query(f"/containers/{container_id}/start")

    # Get the container as json
    container_json = docker_query(f"/containers/{container_id}/json")

    ip = container_json["NetworkSettings"]["Networks"][0]["IPAddress"]

    record = UserContainer(
        user_id = user.id,
        challenge_id = challenge.id,
        container_id = container_id,
        ip = ip
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"ip": ip})
