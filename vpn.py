from .container_controlers import docker_query, docker_exec
import requests

CONTAINER_NAME = "ctfd-openvpn"
IMAGE_NAME = "kylemanna/openvpn:latest"
VOLUME_NAME = "ovpn-data"

def ensure_volume():
    """
    Ensures that the volume for the container exists
    """

    data = docker_query("/volumes")

    # Check if it already exists
    if VOLUME_NAME in [volume["Name"] for volume in data["Volumes"]]:
        docker_query(f"/volumes/{VOLUME_NAME}?force=true", "DELETE")
    
    # otherwise create it
    docker_query("/volumes/create", "POST", { "Name": VOLUME_NAME })

def download_image():
    # Check if it already exists
    try:
        # This will throw a value error, if the image does not exist
        images = docker_query(f"/images/{IMAGE_NAME.split(':')[0]}/json")
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
        if CONTAINER_NAME in container["Names"]:
            if container["State"] != "Running":
                docker_query(f"/containers/{container['Id']}/start", "POST")
            return container["Id"]

    # If it isn't then create one
    payload = {
        "Image": "kylemanna/openvpn",
        "Cmd": ["ovpn_run"],
        "HostConfig": {
            "CapAdd": ["NET_ADMIN"],
            "Binds": [f"{VOLUME_NAME}:/etc/openvpn"],
            "PortBindings": {
                "1194/tcp": [{"HostPort": "443"}]
            }
        },
        "ExposedPorts": {
            "1194/tcp": {}
        }
    }

    download_image()

    result = docker_query(
        f"/containers/create?name={CONTAINER_NAME}",
        "POST",
        payload
    )

    # And then run it
    cid = result["Id"]
    docker_query(f"/containers/{cid}/start", "POST")
    return cid


def init_openvpn():
    """
    This function is used to set up the volume for the openvpn container
    """

    response = requests.get('https://ifconfig.me')
    if response.status_code != 200:
        raise ConnectionRefusedError(f"Could not connect to ifconfig.me to get the machines external ip: {response.status_code}")
    external_ip = response.text.strip()

    # Create the config
    docker_exec(
        CONTAINER_NAME,
        [
            "ovpn_genconfig",
            "-u", f"tcp://{external_ip}:443",
            "-s", "10.8.0.0/24",
            "-p", "route 172.17.0.0 255.255.0.0"
        ]
    )

    # Create the keys for the connections
    docker_exec(CONTAINER_NAME, ["ovpn_initpki"])


def generate_user_vpn(username : str):
    """
    This creates the openvpn config for that user
    
    :param username: the username of the user
    """

    # Sanatise username
    username = ''.join(c for c in username if c.isalnum())

    docker_exec(
        CONTAINER_NAME,
        ["easyrsa", "build-client-full", username, "nopass"]
    )

    ovpn = docker_exec(
        CONTAINER_NAME,
        ["ovpn_getclient", username]
    )

    return ovpn.decode()
