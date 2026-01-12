import math

from CTFd.models import Solves, db
from CTFd.plugins.challenges import BaseChallenge
from CTFd.utils.user import get_current_user

from .models import DockerChallenge


class DockerChallengeType(BaseChallenge):
    id = "docker"
    name = "docker"
    description = "Spins up a Docker container per user"

    templates = {
        "create": "/plugins/docker_challenges/templates/create.html",
        "update": "/plugins/docker_challenges/templates/update.html",
        "view": "/plugins/docker_challenges/templates/view.html",
    }

    scripts = {
        "create": "/plugins/docker_challenges/templates/create.js",
        "update": "/plugins/docker_challenges/templates/update.js",
        "view": "/plugins/docker_challenges/templates/view.js",
    }

    route = "/plugins/docker_challenges/templates/"

    challenge_model = DockerChallenge

    @classmethod
    def calculate_value(cls, challenge):
        """
        Calculate the current value of a challenge based on solves.
        This implements dynamic scoring logic.
        """
        Model = cls.challenge_model

        solve_count = (
            Solves.query.join(Model, Solves.challenge_id == Model.id)
            .filter(
                Solves.challenge_id == challenge.id,
                Model.id == challenge.id,
            )
            .count()
        )

        # Get the dynamic parameters
        minimum = challenge.minimum
        initial = challenge.initial
        decay = challenge.decay

        # Calculate value based on function type
        if challenge.function == "logarithmic":
            value = (((minimum - initial) / (decay**2)) * (solve_count**2)) + initial
        else:  # linear
            value = (minimum - initial) / decay * solve_count + initial

        value = math.ceil(value)

        # Clamp to min
        if value < minimum:
            value = minimum

        return value

    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.
        """
        data = super().read(challenge)

        # Add dynamic scoring info
        data["initial"] = challenge.initial
        data["minimum"] = challenge.minimum
        data["decay"] = challenge.decay
        data["function"] = challenge.function

        # Calculate and add current value
        data["value"] = cls.calculate_value(challenge)

        return data

    @classmethod
    def create(cls, request):
        """
        This method is used to process the challenge creation request.
        """
        data = request.form or request.get_json()

        # Ensure dynamic scoring fields are present with defaults
        data.setdefault("initial", 500)
        data.setdefault("minimum", 100)
        data.setdefault("decay", 50)
        data.setdefault("function", "logarithmic")

        # Remove 'value' if present since we calculate it dynamically
        data.pop("value", None)

        challenge = cls.challenge_model(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        """
        This method is used to update the information associated with a challenge.
        """
        data = request.form or request.get_json()

        for attr, value in data.items():
            # Don't update value directly since it's calculated
            if attr != "value":
                setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)

        DockerChallengeType.calculate_value(challenge)
