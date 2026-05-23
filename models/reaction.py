from datetime import datetime
from models import db


class TopicReaction(db.Model):
    __tablename__ = 'topic_reactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    reaction_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'topic_id', name='uq_user_topic_reaction'),
    )

    REACTION_TYPES = ['Important', 'Interested', 'Discuss Locally', 'Needs Fact Check']
