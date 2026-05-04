from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from models import db, Profile, City, Specialty, ProfileImage, Payment
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
import re

profiles_bp = Blueprint('profiles', __name__)

TIER_PRICES = {
    'basico': 5,
    'profesional': 20,
    'premium': 35
}

TIER_NAMES = {
    'basico': 'Básico — $5/mes',
    'profesional': 'Profesional — $20/mes',
    'premium': 'Premium — $35/mes'
}

OPENING_FEE = 100

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'ñ', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text.strip('-')


@profiles_bp.route('/bufetes')
def list_profiles():
    page = request.args.get('page', 1, type=int)
    profiles = Profile.query.filter_by(status='active').order_by(
        db.case(
            (Profile.tier == 'premium', 0),
            (Profile.tier == 'profesional', 1),
            else_=2
        )
    ).paginate(page=page, per_page=24, error_out=False)
    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()
    return render_template('profiles/list.html', profiles=profiles, cities=cities, specialties=specialties)


@profiles_bp.route('/bufetes/<path:slug>')
def profile_detail(slug):
    # Remove trailing page numbers
    slug = re.sub(r'/\d+$', '', slug)

    profile = Profile.query.filter_by(slug=slug).first()

    if not profile:
        abort(404)

    if profile.status == 'available':
        return render_template('profiles/claim.html', profile=profile,
                               tiers=TIER_PRICES, tier_names=TIER_NAMES,
                               opening_fee=OPENING_FEE)

    if profile.status in ('pending_payment',):
        return render_template('profiles/pending.html', profile=profile)

    related = []
    if profile.city_rel and profile.specialties:
        related = Profile.query.filter(
            Profile.status == 'active',
            Profile.city_id == profile.city_id,
            Profile.id != profile.id
        ).limit(4).all()

    return render_template('profiles/detail.html', profile=profile, related=related)


@profiles_bp.route('/bufetes/<slug>/reclamar', methods=['GET', 'POST'])
def claim_profile(slug):
    profile = Profile.query.filter_by(slug=slug).first_or_404()

    if profile.status != 'available':
        flash('Este perfil ya no está disponible para reclamar.', 'warning')
        return redirect(url_for('profiles.profile_detail', slug=slug))

    if request.method == 'POST':
        tier = request.form.get('tier', 'basico')
        if tier not in TIER_PRICES:
            tier = 'basico'

        if not current_user.is_authenticated:
            # Store in session and redirect to register
            from flask import session
            session['claim_slug'] = slug
            session['claim_tier'] = tier
            flash('Crea una cuenta para continuar con el proceso de reclamación.', 'info')
            return redirect(url_for('auth.register'))

        return redirect(url_for('payments.initiate_payment',
                                profile_id=profile.id,
                                tier=tier,
                                payment_type='opening_fee'))

    return render_template('profiles/claim.html', profile=profile,
                           tiers=TIER_PRICES, tier_names=TIER_NAMES,
                           opening_fee=OPENING_FEE)


@profiles_bp.route('/nuevo-perfil', methods=['GET', 'POST'])
@login_required
def new_profile():
    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        city_id = request.form.get('city_id')
        specialty_ids = request.form.getlist('specialty_ids')
        tier = request.form.get('tier', 'basico')

        if not name:
            flash('El nombre es obligatorio.', 'danger')
            return render_template('profiles/new.html', cities=cities, specialties=specialties,
                                   tiers=TIER_PRICES, tier_names=TIER_NAMES, opening_fee=OPENING_FEE)

        slug = slugify(name)
        base_slug = slug
        counter = 1
        while Profile.query.filter_by(slug=slug).first():
            slug = f'{base_slug}-{counter}'
            counter += 1

        profile = Profile(
            slug=slug,
            name=name,
            city_id=city_id if city_id else None,
            user_id=current_user.id,
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            description=request.form.get('description', ''),
            tier=tier,
            status='pending_payment',
            is_legacy=False
        )

        if specialty_ids:
            specs = Specialty.query.filter(Specialty.id.in_(specialty_ids)).all()
            profile.specialties = specs

        db.session.add(profile)
        db.session.commit()

        return redirect(url_for('payments.initiate_payment',
                                profile_id=profile.id,
                                tier=tier,
                                payment_type='opening_fee'))

    return render_template('profiles/new.html', cities=cities, specialties=specialties,
                           tiers=TIER_PRICES, tier_names=TIER_NAMES, opening_fee=OPENING_FEE)


@profiles_bp.route('/mi-perfil', methods=['GET', 'POST'])
@login_required
def my_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('profiles.new_profile'))

    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()

    if request.method == 'POST':
        profile.name = request.form.get('name', profile.name).strip()
        profile.description = request.form.get('description', '').strip()
        profile.email = request.form.get('email', '').strip()
        profile.phone = request.form.get('phone', '').strip()
        profile.website = request.form.get('website', '').strip()
        profile.address = request.form.get('address', '').strip()

        city_id = request.form.get('city_id')
        profile.city_id = city_id if city_id else None

        specialty_ids = request.form.getlist('specialty_ids')
        if specialty_ids:
            profile.specialties = Specialty.query.filter(Specialty.id.in_(specialty_ids)).all()
        else:
            profile.specialties = []

        # Handle image upload
        if 'images' in request.files:
            files = request.files.getlist('images')
            for f in files:
                if f and f.filename:
                    try:
                        if current_app.config.get('CLOUDINARY_URL'):
                            result = cloudinary.uploader.upload(f, folder='abogados-co')
                            img = ProfileImage(
                                profile_id=profile.id,
                                url=result['secure_url'],
                                cloudinary_public_id=result['public_id'],
                                is_primary=(len(profile.images) == 0)
                            )
                            db.session.add(img)
                    except Exception:
                        pass

        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('profiles.my_profile'))

    return render_template('profiles/edit.html', profile=profile,
                           cities=cities, specialties=specialties)


@profiles_bp.route('/mi-perfil/eliminar-imagen/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    img = ProfileImage.query.get_or_404(image_id)
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    if img.profile_id != profile.id:
        abort(403)
    if img.cloudinary_public_id and current_app.config.get('CLOUDINARY_URL'):
        try:
            cloudinary.uploader.destroy(img.cloudinary_public_id)
        except Exception:
            pass
    db.session.delete(img)
    db.session.commit()
    flash('Imagen eliminada.', 'success')
    return redirect(url_for('profiles.my_profile'))


@profiles_bp.route('/mi-perfil/eliminar', methods=['POST'])
@login_required
def delete_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()

    # Delete cloudinary images
    for img in profile.images:
        if img.cloudinary_public_id and current_app.config.get('CLOUDINARY_URL'):
            try:
                cloudinary.uploader.destroy(img.cloudinary_public_id)
            except Exception:
                pass

    # Reset to available (preserve slug for SEO)
    profile.status = 'available'
    profile.user_id = None
    profile.name = None
    profile.description = None
    profile.email = None
    profile.phone = None
    profile.website = None
    profile.address = None
    profile.specialties = []
    for img in profile.images:
        db.session.delete(img)

    db.session.commit()
    flash('Tu perfil ha sido eliminado. La URL quedará disponible para otros abogados.', 'info')
    return redirect(url_for('main.index'))


@profiles_bp.route('/bufetes/ciudad/<slug>')
def by_city(slug):
    city = City.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    profiles = Profile.query.filter_by(status='active', city_id=city.id).order_by(
        db.case(
            (Profile.tier == 'premium', 0),
            (Profile.tier == 'profesional', 1),
            else_=2
        )
    ).paginate(page=page, per_page=24, error_out=False)
    return render_template('profiles/by_city.html', city=city, profiles=profiles)


@profiles_bp.route('/bufetes/especialidad/<slug>')
def by_specialty(slug):
    specialty = Specialty.query.filter_by(slug=slug).first_or_404()
    city_slug = request.args.get('ciudad', '')
    page = request.args.get('page', 1, type=int)

    query = Profile.query.filter(
        Profile.status == 'active',
        Profile.specialties.any(id=specialty.id)
    )

    if city_slug:
        city = City.query.filter_by(slug=city_slug).first()
        if city:
            query = query.filter_by(city_id=city.id)

    query = query.order_by(
        db.case(
            (Profile.tier == 'premium', 0),
            (Profile.tier == 'profesional', 1),
            else_=2
        )
    )

    profiles = query.paginate(page=page, per_page=24, error_out=False)
    cities = City.query.order_by(City.name).all()
    return render_template('profiles/by_specialty.html',
                           specialty=specialty, profiles=profiles,
                           cities=cities, selected_city=city_slug)
