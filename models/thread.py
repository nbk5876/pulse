from datetime import datetime
from models import db


class ThreadPost(db.Model):
    __tablename__ = 'thread_posts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('thread_posts.id'), nullable=True)

    user = db.relationship('User', backref='thread_posts', lazy=True)
    replies = db.relationship('ThreadPost',
                              backref=db.backref('parent', remote_side='ThreadPost.id'),
                              foreign_keys='ThreadPost.parent_id',
                              lazy=True,
                              order_by='ThreadPost.created_at')
