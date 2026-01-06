import time

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from CTFd.models import db
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user

from . import vpn
from .container_controlers import docker_query
from .models import DockerChallenge, UserContainer

docker_bp = Blueprint("docker", __name__, template_folder="templates")


@docker_bp.route("/docker/spawn/<int:challenge_id>", methods=["POST"])
@authed_only
def spawn_container(challenge_id):
    user = get_current_user()
    challenge = DockerChallenge.query.get_or_404(challenge_id)

    existing = UserContainer.query.filter_by(user_id=user.id).first()
    if existing:
        if existing.challenge_id == challenge_id:
            return jsonify(
                {
                    "success": True,
                    "ip": existing.ip,
                    "expiry_time": existing.expiry_time,
                }
            )
        else:
            other_challenge = DockerChallenge.query.get_or_404(existing.challenge_id)
            return jsonify(
                {"success": False, "error_code": 409, "challenge": other_challenge.name}
            )

    # Create the container
    data = {"Image": challenge.image}
    container_id = docker_query("/containers/create", "POST", data)["Id"]

    # Start the container
    docker_query(f"/containers/{container_id}/start", "POST")

    # Get the container as json
    container_json = docker_query(f"/containers/{container_id}/json")

    ip = next(iter(container_json["NetworkSettings"]["Networks"].values()))["IPAddress"]

    expiry_time = int(time.time()) + 60 * 30  # the current time plus 30 minutes

    record = UserContainer(
        user_id=user.id,
        challenge_id=challenge.id,
        container_id=container_id,
        ip=ip,
        expiry_time=expiry_time,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"success": True, "ip": ip, "expiry_time": expiry_time})


@docker_bp.route("/docker/expiry/expand/<int:challenge_id>", methods=["POST"])
@authed_only
def increase_expiry_time(challenge_id):
    user = get_current_user()

    existing = UserContainer.query.filter_by(user_id=user.id).first()
    if not existing:
        abort(404)

    # increase the expiry time
    existing.expiry_time += 60 * 15  # add 15 minutes till expiry
    db.session.commit()

    return jsonify({"success": True, "expiry_time": existing.expiry_time})


@docker_bp.route("/docker/kill/<int:challenge_id>", methods=["POST"])
@authed_only
def kill_container(challenge_id):
    user = get_current_user()

    existing = UserContainer.query.filter_by(user_id=user.id).first()
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
        return jsonify({"success": True, "status": False})

    # As it exists, return the ip
    container_json = docker_query(f"/containers/{existing.container_id}/json")

    ip = next(iter(container_json["NetworkSettings"]["Networks"].values()))["IPAddress"]

    return jsonify({"success": True, "ip": ip, "expiry_time": existing.expiry_time})


@docker_bp.route("/docker/ovpn/config", methods=["GET"])
@authed_only
def get_openvpn():
    user = get_current_user()
    ovpn_content = vpn.generate_user_vpn(user.name)

    return Response(
        ovpn_content,
        200,
        mimetype="application/x-openvpn-profile",
        headers={"Content-Disposition": f"attachment; filename={user.name}.ovpn"},
    )


@docker_bp.route("/admin/docker_challenges", methods=["GET", "POST"])
@admins_only
def config_page():
    ## Configs are:
    # CA_key_phrase
    # common_name

    if request.method == "POST":
        external_gateway = request.form.get("external_gateway")
        set_config("docker_challenges:external_gateway", external_gateway)

        ca_name = request.form.get("ca_name")
        set_config("docker_challenges:ca_name", ca_name)
        return redirect(url_for("docker.config_page"))

    external_gateway = get_config("docker_challenges:external_gateway")
    ca_name = get_config("docker_challenges:ca_name")

    return render_template(
        "admin.html",
        external_gateway=external_gateway,
        ca_name=ca_name,
    )


@docker_bp.route("/docker/vpn", methods=["GET", "POST", "DELETE"])
@admins_only
def run_vpn():
    if request.method == "POST":
        vpn.ensure_volume()
        vpn.ensure_openvpn()
        return jsonify({"success": True})
    elif request.method == "DELETE":
        vpn.delete_container()
        vpn.delete_volume()
        return jsonify({"success": True})
    elif request.method == "GET":
        container_running = vpn.check_container()
        return jsonify({"success": True, "status": container_running})
