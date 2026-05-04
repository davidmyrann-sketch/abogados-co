"""
Seed the database with cities, specialties, and legacy profile slugs from Wayback Machine.
Run: python seed.py
"""
import sys
from app import create_app
from models import db, City, Specialty, Profile

CITIES = [
    ('bogota', 'Bogotá', 'Cundinamarca'),
    ('medellin', 'Medellín', 'Antioquia'),
    ('cali', 'Cali', 'Valle del Cauca'),
    ('barranquilla', 'Barranquilla', 'Atlántico'),
    ('cartagena-de-indias', 'Cartagena', 'Bolívar'),
    ('bucaramanga', 'Bucaramanga', 'Santander'),
    ('pereira', 'Pereira', 'Risaralda'),
    ('manizales', 'Manizales', 'Caldas'),
    ('cucuta', 'Cúcuta', 'Norte de Santander'),
    ('ibague', 'Ibagué', 'Tolima'),
    ('neiva', 'Neiva', 'Huila'),
    ('santa-marta', 'Santa Marta', 'Magdalena'),
    ('villavicencio', 'Villavicencio', 'Meta'),
    ('armenia', 'Armenia', 'Quindío'),
    ('pasto', 'Pasto', 'Nariño'),
    ('monteria', 'Montería', 'Córdoba'),
    ('popayan', 'Popayán', 'Cauca'),
    ('valledupar', 'Valledupar', 'Cesar'),
    ('sincelejo', 'Sincelejo', 'Sucre'),
    ('riohacha', 'Riohacha', 'La Guajira'),
    ('quibdo', 'Quibdó', 'Chocó'),
    ('florencia', 'Florencia', 'Caquetá'),
    ('mocoa', 'Mocoa', 'Putumayo'),
    ('yopal', 'Yopal', 'Casanare'),
    ('arauca', 'Arauca', 'Arauca'),
    ('duitama', 'Duitama', 'Boyacá'),
    ('tunja', 'Tunja', 'Boyacá'),
    ('bogota-centro', 'Bogotá Centro', 'Cundinamarca'),
    ('bogota-norte', 'Bogotá Norte', 'Cundinamarca'),
    ('bogota-sur', 'Bogotá Sur', 'Cundinamarca'),
    ('bogota-nor-oriente', 'Bogotá Nor-Oriente', 'Cundinamarca'),
    ('antioquia', 'Antioquia', 'Antioquia'),
    ('atlantico', 'Atlántico', 'Atlántico'),
    ('bolivar', 'Bolívar', 'Bolívar'),
    ('boyaca-departamento', 'Boyacá', 'Boyacá'),
    ('caldas-departamento', 'Caldas', 'Caldas'),
    ('casanare', 'Casanare', 'Casanare'),
    ('cauca', 'Cauca', 'Cauca'),
    ('cesar', 'Cesar', 'Cesar'),
    ('cundinamarca', 'Cundinamarca', 'Cundinamarca'),
    ('huila', 'Huila', 'Huila'),
    ('magdalena', 'Magdalena', 'Magdalena'),
    ('meta', 'Meta', 'Meta'),
    ('narino-departamento', 'Nariño', 'Nariño'),
    ('norte-de-santander', 'Norte de Santander', 'Norte de Santander'),
    ('quindio', 'Quindío', 'Quindío'),
    ('risaralda-departamento', 'Risaralda', 'Risaralda'),
    ('santander', 'Santander', 'Santander'),
    ('tolima', 'Tolima', 'Tolima'),
    ('valle-del-cauca', 'Valle del Cauca', 'Valle del Cauca'),
]

SPECIALTIES = [
    ('accion-de-tutela', 'Acción de Tutela', 'Constitutional Protection (Tutela)'),
    ('accion-de-cumplimiento', 'Acción de Cumplimiento', 'Compliance Action'),
    ('acciones-de-grupo', 'Acciones de Grupo', 'Class Actions'),
    ('acciones-populares', 'Acciones Populares', 'Public Interest Actions'),
    ('acciones-electorales', 'Acciones Electorales', 'Electoral Law'),
    ('acoso-laboral', 'Acoso Laboral', 'Workplace Harassment'),
    ('adopciones', 'Adopciones', 'Adoptions'),
    ('adquisiciones', 'Adquisiciones', 'Mergers & Acquisitions'),
    ('aduanas', 'Aduanas', 'Customs Law'),
    ('arbitraje', 'Arbitraje', 'Arbitration'),
    ('asesoria', 'Asesoría Jurídica', 'Legal Advisory'),
    ('auditorias', 'Auditorías', 'Audits'),
    ('capitulaciones', 'Capitulaciones', 'Prenuptial Agreements'),
    ('cobro-juridico', 'Cobro Jurídico', 'Debt Collection'),
    ('comercio-electronico', 'Comercio Electrónico', 'E-Commerce Law'),
    ('comercio-exterior', 'Comercio Exterior', 'International Trade'),
    ('competencia', 'Derecho de Competencia', 'Competition Law'),
    ('conciliaciones', 'Conciliaciones', 'Mediation & Conciliation'),
    ('contencioso-administrativo', 'Contencioso Administrativo', 'Administrative Litigation'),
    ('contratacion-publica', 'Contratación Pública', 'Public Procurement'),
    ('contrato-arrendamiento', 'Contrato de Arrendamiento', 'Lease Agreements'),
    ('contratos', 'Contratos', 'Contracts'),
    ('contratos-de-trabajo', 'Contratos de Trabajo', 'Employment Contracts'),
    ('derecho-administrativo', 'Derecho Administrativo', 'Administrative Law'),
    ('derecho-civil', 'Derecho Civil', 'Civil Law'),
    ('derecho-comercial', 'Derecho Comercial', 'Commercial Law'),
    ('derecho-constitucional', 'Derecho Constitucional', 'Constitutional Law'),
    ('derecho-de-familia', 'Derecho de Familia', 'Family Law'),
    ('derecho-laboral', 'Derecho Laboral', 'Labour Law'),
    ('derecho-penal', 'Derecho Penal', 'Criminal Law'),
    ('derecho-tributario', 'Derecho Tributario', 'Tax Law'),
    ('divorcios', 'Divorcios', 'Divorce'),
    ('herencias', 'Herencias y Sucesiones', 'Inheritance & Estates'),
    ('immigration', 'Inmigración', 'Immigration'),
    ('insolvencia', 'Insolvencia y Quiebra', 'Insolvency & Bankruptcy'),
    ('licitaciones', 'Licitaciones', 'Public Tenders'),
    ('propiedad-horizontal', 'Propiedad Horizontal', 'Condominium Law'),
    ('propiedad-intelectual', 'Propiedad Intelectual', 'Intellectual Property'),
    ('seguros', 'Derecho de Seguros', 'Insurance Law'),
    ('sociedades', 'Derecho de Sociedades', 'Corporate Law'),
]

def _load_legacy_slugs():
    import os
    slugs_file = os.path.join(os.path.dirname(__file__), 'legacy_slugs.txt')
    if os.path.exists(slugs_file):
        with open(slugs_file) as f:
            return [line.strip() for line in f if line.strip()]
    return []

LEGACY_SLUGS = _load_legacy_slugs()


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Cities
        for slug, name, dept in CITIES:
            if not City.query.filter_by(slug=slug).first():
                db.session.add(City(slug=slug, name=name, department=dept))
        db.session.commit()
        print(f"Cities: {City.query.count()}")

        # Specialties
        for slug, name, name_en in SPECIALTIES:
            existing = Specialty.query.filter_by(slug=slug).first()
            if existing:
                existing.name_en = name_en
            else:
                db.session.add(Specialty(slug=slug, name=name, name_en=name_en))
        db.session.commit()
        print(f"Specialties: {Specialty.query.count()}")

        # Legacy profile slugs
        added = 0
        for slug in LEGACY_SLUGS:
            if not Profile.query.filter_by(slug=slug).first():
                db.session.add(Profile(slug=slug, status='available', is_legacy=True))
                added += 1
        db.session.commit()
        print(f"Legacy profiles added: {added}, total: {Profile.query.count()}")

        print("Seed complete.")


if __name__ == '__main__':
    seed()
