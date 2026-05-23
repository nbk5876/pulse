from datetime import datetime
from models import db

user_interests = db.Table(
    'user_interests',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interests.id'), primary_key=True)
)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    political_alignment = db.Column(db.String(50))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    interests = db.relationship('Interest', secondary=user_interests, backref='users', lazy=True)
    reactions = db.relationship('TopicReaction', backref='user', lazy=True)


class Interest(db.Model):
    __tablename__ = 'interests'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Interest {self.name}>'
