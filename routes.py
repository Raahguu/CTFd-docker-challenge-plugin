from flask import Blueprint, jsonify, abort, Response
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user
from .models import UserContainer, DockerChallenge
from CTFd.models import db
import time
from .container_controlers import docker_query
from .vpn import generate_user_vpn


docker_bp = Blueprint("docker", __name__)


@docker_bp.route("/docker/spawn/<int:challenge_id>", methods=["POST"])
@authed_only
def spawn_container(challenge_id):
    user = get_current_user()
    challenge = DockerChallenge.query.get_or_404(challenge_id)

    existing = UserContainer.query.filter_by(
        user_id=user.id
    ).first()
    if existing:
        if existing.challenge_id == challenge_id:
            return jsonify({"success": True, "ip": existing.ip, "expiry_time": existing.expiry_time})
        else:
            other_challenge = DockerChallenge.query.get_or_404(existing.challenge_id)
            return jsonify({"success": False, "error_code": 409, "challenge": other_challenge.name})

    # Create the container
    data = {
        "Image": challenge.image
    }
    container_id = docker_query("/containers/create", "POST", data)["Id"]

    # Start the container
    docker_query(f"/containers/{container_id}/start", "POST")

    # Get the container as json
    container_json = docker_query(f"/containers/{container_id}/json")

    ip = next(iter(container_json["NetworkSettings"]["Networks"].values()))["IPAddress"]

    expiry_time = int(time.time()) + 60 * 30 # the current time plus 30 minutes

    record = UserContainer(
        user_id = user.id,
        challenge_id = challenge.id,
        container_id = container_id,
        ip = ip,
        expiry_time = expiry_time
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"success": True, "ip": ip, "expiry_time": expiry_time})

@docker_bp.route("/docker/expiry/expand/<int:challenge_id>", methods=["POST"])
@authed_only
def increase_expiry_time(challenge_id):
    user = get_current_user()

    existing = UserContainer.query.filter_by(
        user_id=user.id
    ).first()
    if not existing:
        abort(404)

    # increase the expiry time
    existing.expiry_time += 60 * 15 # add 15 minutes till expiry
    db.session.commit()

    return jsonify({"success": True, "expiry_time": existing.expiry_time})

@docker_bp.route("/docker/kill/<int:challenge_id>", methods=["POST"])
@authed_only
def kill_container(challenge_id):
    user = get_current_user()

    existing = UserContainer.query.filter_by(
        user_id=user.id
    ).first()
    if not existing:
        abort(404)

    # Delete the container
    docker_query(f"/containers/{existing.container_id}?force=true", "DELETE")

    db.session.delete(existing)
    db.session.commit()

    return jsonify({"success": True})

@docker_bp.route("/docker/status/<int:challenge_id>", methods=["GET"])
@authed_only
def check_container(challenge_id):
    user = get_current_user()
    challenge = DockerChallenge.query.get_or_404(challenge_id)

    existing = UserContainer.query.filter_by(
        user_id=user.id, challenge_id=challenge.id
    ).first()
    if not existing:
        return jsonify({"status": False})
    
    # As it exists, return the ip
    container_json = docker_query(f"/containers/{existing.container_id}/json")

    ip = next(iter(container_json["NetworkSettings"]["Networks"].values()))["IPAddress"]

    return jsonify({"status": True, "ip": ip, "expiry_time": existing.expiry_time})

@docker_bp.route("/docker/openvpn", methods=["GET"])
@authed_only
def get_openvpn():
    user = get_current_user()
    ovpn_content = generate_user_vpn(user.username)

    return Response(
        ovpn_content,
        200,
        mimetype="application/x-openvpn-profile",
        headers={
            "Content-Disposition": f"attachment; filename=redroom_hackathon.ovpn"
        }
    )
