import requests_unixsocket
import time
from threading import Thread
from .models import UserContainer
from CTFd.models import db

def docker_query(path : str, method : str = "GET", body : dict = {}):
    assert path.count(' ') == 0
    path = path.lstrip("/")

    session = requests_unixsocket.Session()
    response = session.request(
        method=method.lower(), 
        url=f'http+unix://%2Fvar%2Frun%2Fdocker.sock/v1.52/{path}', 
        json=body if body else None
    )

    if not response.text: return {}

    data = response.json()
    if "message" in data and data["message"]:
        raise ValueError("Docker Error: " + str(response.status_code) + " " + data["message"])

    return data

def docker_exec(cid, cmd):
    data = docker_query(
        f"/containers/{cid}/exec", 
        "POST", 
        {
            "AttachStdout": True,
            "AttachStderr": True,
            "Cmd": cmd
        }
    )
    exec_id = data["Id"]

    session = requests_unixsocket.Session()
    result = session.post(
        f"http+unix://%2Fvar%2Frun%2Fdocker.sock/v1.52/exec/{exec_id}/start",
        json={"Detach": False, "Tty": False}
    )

    return result.content


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
    expired = UserContainer.query.filter(
        UserContainer.expiry_time <= now
    ).all()

    for uc in expired:
        try:
            docker_query(
                f"/containers/{uc.container_id}?force=true",
                "DELETE"
            )
        except Exception:
            pass  # container already gone

        db.session.delete(uc)

    db.session.commit()