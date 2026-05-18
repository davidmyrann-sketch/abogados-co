from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort, session
from flask_login import login_required, current_user
import resend
from models import db, Profile, City, Specialty, ProfileImage, Payment, ProfileService, Message, ProfileView
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
import re
from translate import translate_profile

profiles_bp = Blueprint('profiles', __name__)

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
    profiles = Profile.query.filter(Profile.status.in_(['active', 'available'])).order_by(
        db.case(
            (Profile.status == 'active', 0),
            else_=1
        ),
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

    if profile.status == 'pending_payment':
        return render_template('profiles/pending.html', profile=profile)

    if profile.status not in ('active', 'available'):
        abort(404)

    related = []
    if profile.city_rel and profile.specialties:
        related = Profile.query.filter(
            Profile.status.in_(['active', 'available']),
            Profile.city_id == profile.city_id,
            Profile.id != profile.id
        ).limit(4).all()

    try:
        db.session.add(ProfileView(profile_id=profile.id))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return render_template('profiles/detail.html', profile=profile, related=related)


@profiles_bp.route('/bufetes/<slug>/reclamar')
def claim_profile(slug):
    return redirect(url_for('profiles.new_profile', claim=slug))


@profiles_bp.route('/nuevo-perfil', methods=['GET', 'POST'])
@login_required
def new_profile():
    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()
    existing_profile = Profile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        city_id = request.form.get('city_id')
        specialty_ids = request.form.getlist('specialty_ids')

        if not name:
            flash('El nombre es obligatorio.', 'danger')
            return render_template('profiles/new.html', cities=cities, specialties=specialties,
                                   existing_profile=existing_profile)

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
            status='pending_payment',
            is_legacy=False
        )

        if specialty_ids:
            specs = Specialty.query.filter(Specialty.id.in_(specialty_ids)).all()
            profile.specialties = specs

        db.session.add(profile)
        db.session.commit()

        return redirect(url_for('payments.start_subscription', profile_id=profile.id))

    return render_template('profiles/new.html', cities=cities, specialties=specialties,
                           existing_profile=existing_profile)


@profiles_bp.route('/mi-perfil', methods=['GET', 'POST'])
@login_required
def my_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('No encontramos un perfil vinculado a tu cuenta. Puedes crear uno nuevo aquí.', 'info')
        return redirect(url_for('profiles.new_profile'))

    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()

    if request.method == 'POST':
        profile.name = request.form.get('name', profile.name).strip()
        profile.email = request.form.get('email', '').strip()
        profile.phone_country_code = request.form.get('phone_country_code', '+57').strip()
        profile.phone = request.form.get('phone', '').strip()
        profile.website = request.form.get('website', '').strip()
        profile.address = request.form.get('address', '').strip()

        new_description = request.form.get('description', '').strip()
        if new_description != (profile.description or ''):
            profile.description = new_description or None
            if new_description:
                translate_profile(profile, new_description, 'description')
            else:
                profile.description_es = None
                profile.description_en = None

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

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    views_30d = ProfileView.query.filter(
        ProfileView.profile_id == profile.id,
        ProfileView.visited_at >= thirty_days_ago
    ).count()
    contacts_30d = Message.query.filter(
        Message.profile_id == profile.id,
        Message.created_at >= thirty_days_ago
    ).count()
    contacts_total = Message.query.filter(
        Message.profile_id == profile.id
    ).count()
    replied_msgs = Message.query.filter(
        Message.profile_id == profile.id,
        Message.replied_at.isnot(None)
    ).all()
    if replied_msgs:
        total_sec = sum(
            (m.replied_at - m.created_at).total_seconds()
            for m in replied_msgs
            if m.replied_at and m.created_at and m.replied_at > m.created_at
        )
        avg_sec = total_sec / len(replied_msgs) if total_sec > 0 else 0
        h, m_val = int(avg_sec // 3600), int((avg_sec % 3600) // 60)
        avg_response = f"{h}h {m_val}m" if h > 0 else (f"{m_val}m" if m_val > 0 else "<1m")
    else:
        avg_response = "—"

    stats = {
        'views_30d': views_30d,
        'contacts_30d': contacts_30d,
        'contacts_total': contacts_total,
        'avg_response': avg_response,
        'consultations': profile.consultations_count or 0,
        'clients': profile.clients_count or 0,
    }

    return render_template('profiles/edit.html', profile=profile,
                           cities=cities, specialties=specialties, stats=stats)


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

    import stripe as stripe_lib
    stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
    if stripe_key and profile.stripe_subscription_id:
        stripe_lib.api_key = stripe_key
        try:
            stripe_lib.Subscription.cancel(profile.stripe_subscription_id)
        except Exception:
            pass

    db.session.delete(profile)
    db.session.commit()
    flash('Tu perfil ha sido eliminado.', 'info')
    return redirect(url_for('main.index'))


@profiles_bp.route('/bufetes/ciudad/<slug>')
def by_city(slug):
    city = City.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    profiles = Profile.query.filter(
        Profile.status.in_(['active', 'available']),
        Profile.city_id == city.id
    ).order_by(
        db.case(
            (Profile.status == 'active', 0),
            else_=1
        ),
        db.case(
            (Profile.tier == 'premium', 0),
            (Profile.tier == 'profesional', 1),
            else_=2
        )
    ).paginate(page=page, per_page=24, error_out=False)
    return render_template('profiles/by_city.html', city=city, profiles=profiles)


@profiles_bp.route('/bufetes/<slug>/contacto', methods=['POST'])
def send_contact(slug):
    profile = Profile.query.filter_by(slug=slug, status='active').first_or_404()
    sender_name = request.form.get('sender_name', '').strip()
    sender_email = request.form.get('sender_email', '').strip()
    sender_phone = request.form.get('sender_phone', '').strip()
    body = request.form.get('body', '').strip()

    if not sender_name or not sender_email or not body:
        flash('Por favor completa todos los campos obligatorios.', 'danger')
        return redirect(url_for('profiles.profile_detail', slug=slug))

    msg = Message(
        profile_id=profile.id,
        sender_name=sender_name,
        sender_email=sender_email,
        sender_phone=sender_phone,
        body=body
    )
    db.session.add(msg)
    db.session.commit()

    # Email notification to lawyer
    lawyer_email = profile.email or (profile.user.email if profile.user else None)
    base_url = current_app.config.get('BASE_URL', 'https://abogadoya.com.co')
    if lawyer_email and current_app.config.get('RESEND_API_KEY'):
        try:
            resend.Emails.send({
                "from": current_app.config.get('MAIL_FROM', 'noreply@abogadoya.com.co'),
                "reply_to": sender_email,
                "to": [lawyer_email],
                "subject": f"Nueva consulta de {sender_name} — Abogadoya.com.co",
                "html": f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
  <div style="background:#1a3a5c;padding:24px 32px;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0;font-size:18px">📩 Nueva consulta de un cliente</h2>
  </div>
  <div style="background:#f9f9f9;padding:28px 32px;border-radius:0 0 8px 8px">
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
      <tr><td style="padding:8px 0;color:#6b7280;font-size:13px;width:120px">Nombre</td><td style="padding:8px 0;font-weight:700">{sender_name}</td></tr>
      <tr><td style="padding:8px 0;color:#6b7280;font-size:13px">Email</td><td style="padding:8px 0"><a href="mailto:{sender_email}" style="color:#1a3a5c">{sender_email}</a></td></tr>
      <tr><td style="padding:8px 0;color:#6b7280;font-size:13px">Teléfono</td><td style="padding:8px 0">{sender_phone or '—'}</td></tr>
    </table>
    <div style="background:#fff;border-left:4px solid #1a3a5c;padding:16px 20px;border-radius:0 8px 8px 0;margin-bottom:24px">
      <p style="margin:0;font-size:14px;line-height:1.7;color:#333">{body}</p>
    </div>
    <p style="font-size:13px;color:#6b7280;margin-bottom:16px">Puedes responder directamente a este correo — el cliente recibirá tu respuesta inmediatamente.</p>
    <a href="{base_url}/mi-perfil/mensajes" style="background:#1a3a5c;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:14px">Ver en mi panel →</a>
  </div>
</div>"""
            })
        except Exception:
            pass

    lang = session.get('lang', 'es')
    if lang == 'en':
        flash('Your message has been sent. The lawyer will contact you shortly.', 'success')
    else:
        flash('Tu mensaje ha sido enviado. El abogado se pondrá en contacto contigo pronto.', 'success')
    return redirect(url_for('profiles.profile_detail', slug=slug))


@profiles_bp.route('/mi-perfil/servicios/agregar', methods=['POST'])
@login_required
def add_service():
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    price_from = request.form.get('price_from', '').strip()
    price_to = request.form.get('price_to', '').strip()

    if not title:
        flash('El título del servicio es obligatorio.', 'danger')
        return redirect(url_for('profiles.my_profile'))

    svc = ProfileService(
        profile_id=profile.id,
        title=title,
        description=description or None,
        price_from=int(price_from) if price_from.isdigit() else None,
        price_to=int(price_to) if price_to.isdigit() else None,
        sort_order=len(profile.services)
    )
    db.session.add(svc)
    db.session.flush()
    translate_profile(svc, title, 'title')
    if description:
        translate_profile(svc, description, 'description')
    db.session.commit()
    flash('Servicio añadido.' if session.get('lang') != 'en' else 'Service added.', 'success')
    return redirect(url_for('profiles.my_profile'))


@profiles_bp.route('/mi-perfil/servicios/<int:service_id>/eliminar', methods=['POST'])
@login_required
def delete_service(service_id):
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    svc = ProfileService.query.get_or_404(service_id)
    if svc.profile_id != profile.id:
        abort(403)
    db.session.delete(svc)
    db.session.commit()
    flash('Servicio eliminado.' if session.get('lang') != 'en' else 'Service removed.', 'success')
    return redirect(url_for('profiles.my_profile'))


@profiles_bp.route('/mi-perfil/mensajes')
@login_required
def my_messages():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('profiles.new_profile'))
    msgs = Message.query.filter_by(profile_id=profile.id).order_by(Message.created_at.desc()).all()
    return render_template('profiles/messages.html', messages=msgs, profile=profile)


@profiles_bp.route('/mi-perfil/mensajes/<int:msg_id>/responder', methods=['POST'])
@login_required
def reply_message(msg_id):
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    msg = Message.query.get_or_404(msg_id)
    if msg.profile_id != profile.id:
        abort(403)

    reply_text = request.form.get('reply_text', '').strip()
    if not reply_text:
        flash('La respuesta no puede estar vacía.', 'danger')
        return redirect(url_for('profiles.my_messages'))

    msg.reply_text = reply_text
    msg.replied_at = datetime.utcnow()
    msg.is_read = True
    db.session.commit()

    if current_app.config.get('RESEND_API_KEY'):
        try:
            lawyer_reply_email = profile.email or (profile.user.email if profile.user else None)
            resend.Emails.send({
                "from": current_app.config.get('MAIL_FROM', 'noreply@abogadoya.com.co'),
                "reply_to": lawyer_reply_email,
                "to": [msg.sender_email],
                "subject": f"Respuesta de {profile.name} — Abogadoya.com.co",
                "html": f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
  <div style="background:#1a3a5c;padding:24px 32px;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0;font-size:18px">Respuesta de {profile.name}</h2>
  </div>
  <div style="background:#f9f9f9;padding:28px 32px;border-radius:0 0 8px 8px">
    <p style="margin:0 0 16px">Hola <strong>{msg.sender_name}</strong>,</p>
    <p style="margin:0 0 20px;color:#555;font-size:14px">{profile.name} ha respondido a tu consulta:</p>
    <div style="background:#fff;border-left:4px solid #1a3a5c;padding:16px 20px;border-radius:0 8px 8px 0;margin-bottom:24px">
      <p style="margin:0;font-size:14px;line-height:1.7;color:#333">{reply_text}</p>
    </div>
    <p style="font-size:13px;color:#6b7280">Puedes responder directamente a este correo para continuar la conversación con {profile.name}.</p>
    <hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0">
    <p style="font-size:12px;color:#aaa;margin:0">Abogadoya.com.co — Directorio jurídico de Colombia</p>
  </div>
</div>"""
            })
        except Exception:
            pass

    flash('Respuesta enviada.' if session.get('lang') != 'en' else 'Reply sent.', 'success')
    return redirect(url_for('profiles.my_messages'))


@profiles_bp.route('/mi-perfil/mensajes/<int:msg_id>/leer', methods=['POST'])
@login_required
def mark_read(msg_id):
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    msg = Message.query.get_or_404(msg_id)
    if msg.profile_id != profile.id:
        abort(403)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('profiles.my_messages'))


@profiles_bp.route('/mi-perfil/reportar-consulta', methods=['POST'])
@login_required
def report_consultation():
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    profile.consultations_count = (profile.consultations_count or 0) + 1
    db.session.commit()
    flash('Consulta registrada.' if session.get('lang') != 'en' else 'Consultation recorded.', 'success')
    return redirect(url_for('profiles.my_profile'))


@profiles_bp.route('/mi-perfil/reportar-cliente', methods=['POST'])
@login_required
def report_client():
    profile = Profile.query.filter_by(user_id=current_user.id).first_or_404()
    profile.clients_count = (profile.clients_count or 0) + 1
    db.session.commit()
    flash('Cliente registrado.' if session.get('lang') != 'en' else 'Client recorded.', 'success')
    return redirect(url_for('profiles.my_profile'))


@profiles_bp.route('/bufetes/especialidad/<slug>')
def by_specialty(slug):
    specialty = Specialty.query.filter_by(slug=slug).first_or_404()
    city_slug = request.args.get('ciudad', '')
    page = request.args.get('page', 1, type=int)

    query = Profile.query.filter(
        Profile.status.in_(['active', 'available']),
        Profile.specialties.any(id=specialty.id)
    )

    if city_slug:
        city = City.query.filter_by(slug=city_slug).first()
        if city:
            query = query.filter_by(city_id=city.id)

    query = query.order_by(
        db.case(
            (Profile.status == 'active', 0),
            else_=1
        ),
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
