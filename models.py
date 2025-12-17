from CTFd.models import db, Challenges
from CTFd.exceptions.challenges import (
    ChallengeCreateException,
    ChallengeUpdateException,
)

class DockerChallenge(Challenges):
    __tablename__ = "docker_challenges"
    id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True)
    image = db.Column(db.String(128))

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
        
    

class UserContainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"))
    container_id = db.Column(db.String(64))
    ip = db.Column(db.String(64)) 
    expiry_time = db.Column(db.Integer) # UNIX timestamp