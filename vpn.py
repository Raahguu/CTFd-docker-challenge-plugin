from json.decoder import JSONDecodeError

from CTFd.utils import get_config

from .container_controlers import (
    docker_query,
    docker_read_logs,
)

CONTAINER_NAME = "ctfd-openvpn"
IMAGE_NAME = "kylemanna/openvpn:2.4"
VOLUME_NAME = "ovpn-data"


def ensure_volume():
    """
    Ensures that the volume for the container exists
    """

    try:
        data = docker_query("/volumes")
        # Check if it already exists
        if VOLUME_NAME in [volume["Name"] for volume in data["Volumes"]]:
            docker_query(f"/volumes/{VOLUME_NAME}?force=true", "DELETE")
    except:
        pass

    # otherwise create it
    docker_query("/volumes/create", "POST", {"Name": VOLUME_NAME})
    init_volume()


def download_image():
    # Check if it already exists
    try:
        # This will throw a value error, if the image does not exist
        docker_query(f"/images/{IMAGE_NAME.split(':')[0]}/json")
        return
    except:
        docker_query(f"/images/create?fromImage={IMAGE_NAME}", "POST")


def ensure_openvpn():
    """
    Ensures that the container is up and running
    """

    data = docker_query("/containers/json?all=true")
    # Check if the container already exists
    for container in data:
        if ("/" + CONTAINER_NAME) in container["Names"]:
            if container["State"] != "Running":
                docker_query(f"/containers/{container['Id']}/start", "POST")
            return

    # If it isn't then create one
    payload = {
        "Image": IMAGE_NAME,
        "HostConfig": {
            "CapAdd": ["NET_ADMIN"],
            "Sysctls": {
                "net.ipv6.conf.default.forwarding": "1",
                "net.ipv6.conf.all.forwarding": "1",
                "net.ipv4.ip_forward": "1",
            },
            "Binds": [f"{VOLUME_NAME}:/etc/openvpn"],
            "PortBindings": {"1194/tcp": [{"HostPort": "1194"}]},
        },
        "ExposedPorts": {"1194/tcp": {}},
    }

    download_image()

    result = docker_query(f"/containers/create?name={CONTAINER_NAME}", "POST", payload)

    # And then run it
    cid = result["Id"]
    docker_query(f"/containers/{cid}/start", "POST")
    return


def check_container():
    data = docker_query("/containers/json?all=true")
    # Check if the container already exists
    for container in data:
        if ("/" + CONTAINER_NAME) in container["Names"]:
            if container["State"] != "Running":
                return False
            return True
    return False


def init_volume():
    """
    This function is used to set up the volume for the openvpn container
    """

    ## Download the image if it does not exist
    download_image()

    # Get the neccessary user configs
    external_gateway = get_config("docker_challenges:external_gateway")
    ca_name = get_config("docker_challenges:ca_name")

    script = f"""#!/bin/bash
        set -e
        ovpn_genconfig -u tcp://{external_gateway} -p "route 172.17.0.0 255.255.0.0"
        source "$OPENVPN/ovpn_env.sh"
        easyrsa init-pki
        printf '{ca_name}\n' | easyrsa build-ca nopass
        easyrsa gen-dh
        openvpn --genkey --secret $EASYRSA_PKI/ta.key
        easyrsa build-server-full "$OVPN_CN" nopass
        easyrsa gen-crl
    """

    # Create the container to execute on and give the command
    result = docker_query(
        "/containers/create",
        "POST",
        {
            "Image": IMAGE_NAME,
            "Cmd": ["bash", "-c", script],
            "HostConfig": {
                "Binds": [f"{VOLUME_NAME}:/etc/openvpn"],
                "Autoremove": True,
            },
        },
    )
    cid = result["Id"]

    # Run the container
    docker_query(f"/containers/{cid}/start", "POST")
    # Wait for the container to finish
    docker_query(f"/containers/{cid}/wait", "POST")


def generate_user_vpn(username: str):
    """
    This creates the openvpn config for that user

    :param username: the username of the user
    """

    # Sanatise username
    username = "user_" + "".join(c for c in username if c.isalnum())

    # Add the user
    result = docker_query(
        "/containers/create",
        "POST",
        {
            "Image": IMAGE_NAME,
            "Cmd": ["easyrsa", "build-client-full", username, "nopass"],
            "HostConfig": {
                "Binds": [f"{VOLUME_NAME}:/etc/openvpn"],
                "Autoremove": True,
            },
        },
    )
    cid = result["Id"]
    # Run the container
    docker_query(f"/containers/{cid}/start", "POST")
    # Wait for the container to finish
    docker_query(f"/containers/{cid}/wait", "POST")

    # Get the user's profile
    result = docker_query(
        "/containers/create",
        "POST",
        {
            "Image": IMAGE_NAME,
            "Cmd": ["ovpn_getclient", username],
            "HostConfig": {
                "Binds": [f"{VOLUME_NAME}:/etc/openvpn"],
                # "Autoremove": True,
            },
        },
    )
    cid = result["Id"]

    # Run the container
    docker_query(f"/containers/{cid}/start", "POST")
    # Wait for the container to finish
    docker_query(f"/containers/{cid}/wait", "POST")

    # Get the container's logs as they are the ovpn client
    ovpn = docker_read_logs(cid)

    # Delete the container
    docker_query(f"/containers/{cid}?force=true", "DELETE")

    return ovpn


def delete_container():
    return docker_query(f"/containers/{CONTAINER_NAME}?force=true", "DELETE")


def delete_volume():
    return docker_query(f"/volumes/{VOLUME_NAME}?force=true", "DELETE")
