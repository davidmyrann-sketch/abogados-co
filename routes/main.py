from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, Profile, City, Specialty, ProfileService

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
