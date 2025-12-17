from CTFd.plugins.challenges import BaseChallenge
from CTFd.models import db
from CTFd.utils.user import get_current_user
from .models import DockerChallenge

class DockerChallengeType(BaseChallenge):
    id = "docker"
    name = "docker"
    description = "Spins up a Docker container per user"

    templates = {
        "create": "/plugins/docker_challenges/templates/create.html",
        "update": "/plugins/docker_challenges/templates/update.html",
        "view": "/plugins/docker_challenges/templates/view.html"
    }

    scripts = {
        "create": "/plugins/docker_challenges/templates/create.js",
        "update": "/plugins/docker_challenges/templates/update.js",
        "view": "/plugins/docker_challenges/templates/view.js"
    }

    route = "/plugins/docker_challenges/templates/"

    challenge_model = DockerChallenge

    @classmethod
    def create(cls, request):
        """
        This method is used to process the challenge creation request.

        :param request:
        :return:
        """
        data = request.form or request.get_json()

        challenge = cls.challenge_model(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge