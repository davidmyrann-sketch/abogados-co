import os, sys
os.environ['DATABASE_URL'] = 'postgresql://postgres:iofmFECZQGwbGNCUZvmlJXqjGkrOqEAB@tramway.proxy.rlwy.net:59450/railway'

from app import create_app
from models import db
from sqlalchemy import text
from datetime import datetime

app = create_app()
with app.app_context():
    with open('legacy_slugs.txt') as f:
        slugs = [l.strip() for l in f if l.strip()]
    print(f'Laster {len(slugs)} slugs...')

    now = datetime.utcnow()
    rows = [{'slug': s, 'status': 'available', 'is_legacy': True,
             'tier': 'basico', 'created_at': now, 'updated_at': now}
            for s in slugs]

    result = db.session.execute(
        text("""
            INSERT INTO profiles (slug, status, is_legacy, tier, created_at, updated_at)
            VALUES (:slug, :status, :is_legacy, :tier, :created_at, :updated_at)
            ON CONFLICT (slug) DO NOTHING
        """),
        rows
    )
    db.session.commit()

    total = db.session.execute(text('SELECT COUNT(*) FROM profiles')).scalar()
    available = db.session.execute(text("SELECT COUNT(*) FROM profiles WHERE status='available'")).scalar()
    print(f'Fullført. Total URLer: {total} | Ledige: {available}')
