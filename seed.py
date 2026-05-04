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
    ('accion-de-tutela', 'Acción de Tutela'),
    ('accion-de-cumplimiento', 'Acción de Cumplimiento'),
    ('acciones-de-grupo', 'Acciones de Grupo'),
    ('acciones-populares', 'Acciones Populares'),
    ('acciones-electorales', 'Acciones Electorales'),
    ('acoso-laboral', 'Acoso Laboral'),
    ('adopciones', 'Adopciones'),
    ('adquisiciones', 'Adquisiciones'),
    ('aduanas', 'Aduanas'),
    ('arbitraje', 'Arbitraje'),
    ('asesoria', 'Asesoría Jurídica'),
    ('auditorias', 'Auditorías'),
    ('capitulaciones', 'Capitulaciones'),
    ('cobro-juridico', 'Cobro Jurídico'),
    ('comercio-electronico', 'Comercio Electrónico'),
    ('comercio-exterior', 'Comercio Exterior'),
    ('competencia', 'Derecho de Competencia'),
    ('conciliaciones', 'Conciliaciones'),
    ('contencioso-administrativo', 'Contencioso Administrativo'),
    ('contratacion-publica', 'Contratación Pública'),
    ('contrato-arrendamiento', 'Contrato de Arrendamiento'),
    ('contratos', 'Contratos'),
    ('contratos-de-trabajo', 'Contratos de Trabajo'),
    ('derecho-administrativo', 'Derecho Administrativo'),
    ('derecho-civil', 'Derecho Civil'),
    ('derecho-comercial', 'Derecho Comercial'),
    ('derecho-constitucional', 'Derecho Constitucional'),
    ('derecho-de-familia', 'Derecho de Familia'),
    ('derecho-laboral', 'Derecho Laboral'),
    ('derecho-penal', 'Derecho Penal'),
    ('derecho-tributario', 'Derecho Tributario'),
    ('divorcios', 'Divorcios'),
    ('herencias', 'Herencias y Sucesiones'),
    ('immigration', 'Inmigración'),
    ('insolvencia', 'Insolvencia y Quiebra'),
    ('licitaciones', 'Licitaciones'),
    ('propiedad-horizontal', 'Propiedad Horizontal'),
    ('propiedad-intelectual', 'Propiedad Intelectual'),
    ('seguros', 'Derecho de Seguros'),
    ('sociedades', 'Derecho de Sociedades'),
]

LEGACY_SLUGS = [
    "25-m-abogados-sas","7pilares-alianza-juridica-estrategica","a-c-consultores-juridicos-y-empresariales-sas",
    "a-catalina-diaz-c","aan-abogados-y-asesorias-en-medio-ambiente-inmigracion-y-derecho-privado",
    "abetcol","abetcol-sa","abg-carlos-daniel-martinez-mora","abogada-danny-lorena-giraldo-gomez",
    "abogada-gestiones-juridicas-sas","abogada-gloria-zapata","abogada-jessica-zapata",
    "abogada-lucila-ocampo-ariza","abogada-luz-dary-castillo","abogada-maria-fernanda-leal",
    "abogada-maudy-tovar-cordoba","abogada-monica-elisa-paz-castro","abogada-monica-paz",
    "abogada-monica-paz-online","abogada-natalia-cardozo","abogados-abesco-de-colombia-sas",
    "abogados-asociados-legales","abogados-asociados-total-juridica","abogados-consultores-ac-sas",
    "abogados-hackers","abogados-penalistas-bogota","abogados-penalistas-consultores",
    "ac-abogados-y-consultorias","advocatus","ag-abogados",
    "alejandro-restrepo-zuluaga-abogados-consultores","alexander-jimenez-cuartas-abogado",
    "alexander-silva-pineda-abogado","alfredo-moreno-davila",
    "alianza-consultores-y-tributaristas-sas","alianza-juridica","alvarez-redondo",
    "alvaro-pinzon-guarin-abogados","amadeo-ceron-abogados",
    "ana-maria-vergara-consultorias-juridicas-sas","andrea-cubillos-hernandez",
    "andres-eraso-burbano-juristas-consultores-asociados","ar-abogados-asociados",
    "ar-juridica-especializada","aranguren-calle-y-asociados-abogados","araujo-ibarra",
    "arias-y-aristizabal-abogados-asesores","ariza-soto-asociados-abogados-consultores",
    "arroyave-asociados-consultores-sas","asistencia-juridica-moderna-ddt-sas",
    "asistencia-legal","atenttia","augusto-rico-consultorias",
    "bona-fides-consultores","brigard-y-castro","bufete-de-abogados-consultores",
    "caballero-gomez-palacios","cardona-ocampo","carolina-ramos-y-abogados",
    "castellanos-y-co","castrillon-cardenas-abogados-consultores","cavelier-abogados",
    "cc-abogados-y-gestores-inmobiliarios","chb-abogado","click-abogados-asociados",
    "cm-abogados-asociados","cng-abogados-consultores-sas","colmenares-torres-abogados-asociados",
    "colombia-legal-advisors","con-justicia-y-equidad","consocial-consultores-limitada",
    "consorcio-borrero-martin-asociados-sas","consuelo-jaramillo-de-olarte",
    "consultorias-y-asesorias-especializadas","cartagena-legal-asesorias-legales-y-soluciones",
    "gestionamos","servijuridica","cc-corporacion","abogados-asociados-legales",
]


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
        for slug, name in SPECIALTIES:
            if not Specialty.query.filter_by(slug=slug).first():
                db.session.add(Specialty(slug=slug, name=name))
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
