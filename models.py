from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

profile_specialties = db.Table('profile_specialties',
    db.Column('profile_id', db.Integer, db.ForeignKey('profiles.id')),
    db.Column('specialty_id', db.Integer, db.ForeignKey('specialties.id'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profiles = db.relationship('Profile', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    profiles = db.relationship('Profile', backref='city_rel', lazy=True)


class Specialty(db.Model):
    __tablename__ = 'specialties'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)


class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    website = db.Column(db.String(255))
    address = db.Column(db.String(500))
    tier = db.Column(db.String(20), default='basico')  # basico, profesional, premium
    # available=pre-seeded/unclaimed, pending=paid but not confirmed, active=live, inactive=deactivated
    status = db.Column(db.String(20), default='available')
    is_legacy = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subscription_start = db.Column(db.DateTime)
    next_billing_date = db.Column(db.DateTime)
    specialties = db.relationship('Specialty', secondary=profile_specialties, lazy='subquery',
                                  backref=db.backref('profiles', lazy=True))
    images = db.relationship('ProfileImage', backref='profile', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='profile', lazy=True)


class ProfileImage(db.Model):
    __tablename__ = 'profile_images'
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    cloudinary_public_id = db.Column(db.String(255))
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='usd')
    payment_type = db.Column(db.String(30))  # opening_fee, monthly
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    stripe_session_id = db.Column(db.String(255))
    tier_selected = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
