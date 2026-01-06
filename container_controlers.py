import struct
import time
from json.decoder import JSONDecodeError
from threading import Thread

import requests_unixsocket

from CTFd.models import db

from .models import UserContainer


def docker_query(path: str, method: str = "GET", body: dict = {}):
    assert path.count(" ") == 0
    path = path.lstrip("/")

    session = requests_unixsocket.Session()
    response = session.request(
        method=method.lower(),
        url=f"http+unix://%2Fvar%2Frun%2Fdocker.sock/v1.52/{path}",
        json=body if body else None,
    )

    if not response.text:
        return {}

    try:
        data: dict = response.json()
    except JSONDecodeError as e:
        print(e)
        return response.text
    if "message" in data and data["message"]:
        raise ValueError(
            "Docker Error: " + str(response.status_code) + " " + data["message"]
        )

    return data


def docker_exec(cid: str, cmd: list[str]):
    return docker_query(
        f"/containers/{cid}/exec",
        "POST",
        {
            "AttachStdout": True,
            "AttachStderr": True,
            "Cmd": cmd,
        },
    )


def docker_read_logs(cid: str) -> str:
    session = requests_unixsocket.Session()
    response = session.request(
        method="get",
        url=f"http+unix://%2Fvar%2Frun%2Fdocker.sock/v1.52/containers/{cid}/logs?stdout=1&stderr=1",
        stream=True,
    )
    response.raise_for_status()

    content = response.content

    # Docker log format: 8-byte header + payload (repeated)
    # Header: [stream_type(1), 0, 0, 0, size(4 bytes big-endian)]
    output = []
    offset = 0

    while offset < len(content):
        if offset + 8 > len(content):
            # Not enough bytes for header
            break

        # Read header
        header = content[offset : offset + 8]
        stream_type = header[0]
        # Combine 4 bytes into an int
        size = struct.unpack(">I", header[4:8])[0]

        # Read payload
        offset += 8
        if offset + size > len(content):
            # Not enough bytes for payload
            break

        payload = content[offset : offset + size]
        output.append(payload.decode("utf-8", errors="ignore"))
        offset += size

    return "".join(output)


# Clean up expired containers
def start_cleaner(app):
    def loop():
        while True:
            with app.app_context():
                cleanup_expired_containers()
            time.sleep(30)

    Thread(target=loop, daemon=True).start()


def cleanup_expired_containers():
    now = time.time()
    expired = UserContainer.query.filter(UserContainer.expiry_time <= now).all()

    for uc in expired:
        try:
            docker_query(f"/containers/{uc.container_id}?force=true", "DELETE")
        except Exception:
            pass  # container already gone

        db.session.delete(uc)

    db.session.commit()
