from datetime import datetime
from models import db


class Topic(db.Model):
    __tablename__ = 'topics'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active_flag = db.Column(db.Boolean, default=True)

    sources = db.relationship('TopicSource', backref='topic', lazy=True, cascade='all, delete-orphan')
    reactions = db.relationship('TopicReaction', backref='topic', lazy=True, cascade='all, delete-orphan')


class UserHiddenTopic(db.Model):
    __tablename__ = 'user_hidden_topics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'topic_id'),)


class TopicSource(db.Model):
    __tablename__ = 'topic_sources'

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    source_name = db.Column(db.String(200))
    source_url = db.Column(db.String(500))
