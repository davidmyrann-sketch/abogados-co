import os
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
import resend
from models import db, User
from routes.main import main_bp
from routes.profiles import profiles_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.payments import payments_bp


def _apply_migrations(db):
    """Add columns that may be missing from older DB schemas."""
    alterations = [
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_start TIMESTAMP",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS next_billing_date TIMESTAMP",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_legacy BOOLEAN DEFAULT FALSE",
    ]
    for sql in alterations:
        try:
            db.session.execute(db.text(sql))
        except Exception:
            db.session.rollback()
    db.session.commit()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///abogados.db')
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY', '')
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
    app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    app.config['CLOUDINARY_URL'] = os.environ.get('CLOUDINARY_URL', '')
    app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'davidmyrann@gmail.com')
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:5000')

    app.config['RESEND_API_KEY'] = os.environ.get('RESEND_API_KEY', '')
    app.config['MAIL_FROM'] = os.environ.get('MAIL_FROM', 'contact@abogadoya.com.co')

    db.init_app(app)
    Migrate(app, db)

    with app.app_context():
        db.create_all()
        _apply_migrations(db)

    resend_key = app.config.get('RESEND_API_KEY', '')
    if resend_key:
        resend.api_key = resend_key

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(main_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payments_bp)

    from flask import session as flask_session
    from flask_login import current_user

    @app.context_processor
    def inject_globals():
        unread = 0
        if current_user.is_authenticated:
            from models import Profile, Message
            profile = Profile.query.filter_by(user_id=current_user.id).first()
            if profile:
                unread = Message.query.filter_by(profile_id=profile.id, is_read=False).count()
        lang = flask_session.get('lang', 'es')

        def spec_name(spec):
            if lang == 'en' and spec.name_en:
                return spec.name_en
            return spec.name

        return {'lang': lang, 'unread_count': unread, 'spec_name': spec_name}

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
