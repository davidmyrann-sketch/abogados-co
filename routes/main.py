from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, Response, current_app
from models import db, Profile, City, Specialty, ProfileService
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.context_processor
def inject_lang():
    return {'lang': session.get('lang', 'es')}

@main_bp.route('/lang/<lang>')
def set_lang(lang):
    if lang in ('en', 'es'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))

@main_bp.route('/')
def index():
    featured = Profile.query.filter_by(status='active', tier='premium').limit(6).all()
    professional = Profile.query.filter_by(status='active', tier='profesional').limit(6).all()
    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()
    total_profiles = Profile.query.filter_by(status='active').count()
    return render_template('index.html',
                           featured=featured,
                           professional=professional,
                           cities=cities,
                           specialties=specialties,
                           total_profiles=total_profiles)

@main_bp.route('/buscar')
def search():
    q = request.args.get('q', '').strip()
    city_slug = request.args.get('ciudad', '').strip()
    specialty_slug = request.args.get('especialidad', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Profile.query.filter_by(status='active')

    if q:
        query = query.filter(
            db.or_(
                Profile.name.ilike(f'%{q}%'),
                Profile.services.any(ProfileService.title.ilike(f'%{q}%'))
            )
        )
    if city_slug:
        city = City.query.filter_by(slug=city_slug).first()
        if city:
            query = query.filter_by(city_id=city.id)
    if specialty_slug:
        spec = Specialty.query.filter_by(slug=specialty_slug).first()
        if spec:
            query = query.filter(Profile.specialties.any(id=spec.id))

    query = query.order_by(
        db.case(
            (Profile.tier == 'premium', 0),
            (Profile.tier == 'profesional', 1),
            else_=2
        ),
        Profile.name
    )

    profiles = query.paginate(page=page, per_page=20, error_out=False)
    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()

    return render_template('search.html',
                           profiles=profiles,
                           cities=cities,
                           specialties=specialties,
                           q=q,
                           city_slug=city_slug,
                           specialty_slug=specialty_slug)

@main_bp.route('/quienes')
def about():
    return render_template('about.html')

@main_bp.route('/preguntas')
def faq():
    return render_template('faq.html')

@main_bp.route('/robots.txt')
def robots():
    base = current_app.config.get('BASE_URL', 'https://abogadoya.com.co')
    content = f"""User-agent: *
Disallow: /admin
Disallow: /mi-perfil
Disallow: /login
Disallow: /registro
Disallow: /stripe/
Allow: /

Sitemap: {base}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


@main_bp.route('/sitemap.xml')
def sitemap():
    base = current_app.config.get('BASE_URL', 'https://abogadoya.com.co')
    today = datetime.utcnow().strftime('%Y-%m-%d')

    urls = [
        (base + '/', today, 'daily', '1.0'),
        (base + '/bufetes', today, 'daily', '0.9'),
        (base + '/buscar', today, 'daily', '0.8'),
        (base + '/quienes', today, 'monthly', '0.5'),
        (base + '/preguntas', today, 'monthly', '0.5'),
    ]

    cities = City.query.all()
    for city in cities:
        urls.append((base + f'/bufetes/ciudad/{city.slug}', today, 'weekly', '0.7'))

    specialties = Specialty.query.all()
    for spec in specialties:
        urls.append((base + f'/bufetes/especialidad/{spec.slug}', today, 'weekly', '0.7'))

    profiles = Profile.query.filter_by(status='active').all()
    for p in profiles:
        urls.append((base + f'/bufetes/{p.slug}', today, 'weekly', '0.8'))

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for loc, lastmod, changefreq, priority in urls:
        xml_parts.append(f'''  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>''')
    xml_parts.append('</urlset>')

    return Response('\n'.join(xml_parts), mimetype='application/xml')


@main_bp.route('/api/search-suggest')
def search_suggest():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Profile.query.filter(
        Profile.status == 'active',
        Profile.name.ilike(f'%{q}%')
    ).limit(8).all()
    return jsonify([{'name': p.name, 'slug': p.slug} for p in results])
