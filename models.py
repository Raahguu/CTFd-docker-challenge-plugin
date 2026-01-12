from CTFd.exceptions.challenges import ChallengeCreateException
from CTFd.models import Challenges, db


class DockerChallenge(Challenges):
    __tablename__ = "docker_challenges"
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    image = db.Column(db.String(128))

    # initial = db.Column(db.Integer, default=0)
    # minimum = db.Column(db.Integer, default=0)
    # decay = db.Column(db.Integer, default=0)
    # function = db.Column(db.String(32), default="logarithmic")

    __mapper_args__ = {
        "polymorphic_identity": "docker",
        "inherit_condition": id == Challenges.id,
    }

    def __init__(self, *args, **kwargs):
        super(DockerChallenge, self).__init__(**kwargs)
        try:
            self.image = kwargs["image"]
        except KeyError:
            raise ChallengeCreateException("Missing image value for challenge")
        try:
            self.value = kwargs["initial"]
        except KeyError:
            raise ChallengeCreateException("Missing initial value for challenge")

        self.minimum = kwargs.get("minimum", 100)
        self.decay = kwargs.get("decay", 50)
        self.function = kwargs.get("function", "logarithmic")


class UserContainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE")
    )
    container_id = db.Column(db.String(64))
    ip = db.Column(db.String(64))
    expiry_time = db.Column(db.Integer)  # UNIX timestamp
