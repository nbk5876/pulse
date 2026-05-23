from datetime import datetime
from models import db

civic_unit_members = db.Table(
    'civic_unit_members',
    db.Column('civic_unit_id', db.Integer, db.ForeignKey('civic_units.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)


class CivicUnit(db.Model):
    __tablename__ = 'civic_units'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('User', secondary=civic_unit_members, backref='civic_units', lazy=True)
