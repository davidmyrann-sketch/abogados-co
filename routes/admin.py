from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Profile, User, Payment, City, Specialty
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def index():
    stats = {
        'total_profiles': Profile.query.count(),
        'active_profiles': Profile.query.filter_by(status='active').count(),
        'pending_profiles': Profile.query.filter_by(status='pending_payment').count(),
        'available_urls': Profile.query.filter_by(status='available').count(),
        'total_users': User.query.count(),
        'total_payments': Payment.query.filter_by(status='completed').count(),
        'revenue': db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    }
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    pending_profiles = Profile.query.filter_by(status='pending_payment').order_by(Profile.updated_at.desc()).all()
    return render_template('admin/index.html', stats=stats,
                           recent_payments=recent_payments,
                           pending_profiles=pending_profiles)


@admin_bp.route('/perfiles')
@admin_required
def profiles():
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')

    query = Profile.query
    if status:
        query = query.filter_by(status=status)
    if q:
        query = query.filter(Profile.name.ilike(f'%{q}%') | Profile.slug.ilike(f'%{q}%'))

    profiles = query.order_by(Profile.updated_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template('admin/profiles.html', profiles=profiles, status=status, q=q)


@admin_bp.route('/perfiles/<int:profile_id>/editar', methods=['GET', 'POST'])
@admin_required
def edit_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    cities = City.query.order_by(City.name).all()
    specialties = Specialty.query.order_by(Specialty.name).all()

    if request.method == 'POST':
        profile.name = request.form.get('name', '').strip() or None
        profile.status = request.form.get('status', profile.status)
        profile.tier = request.form.get('tier', profile.tier)
        profile.city_id = request.form.get('city_id') or None
        profile.email = request.form.get('email', '').strip() or None
        profile.phone = request.form.get('phone', '').strip() or None
        profile.description = request.form.get('description', '').strip() or None

        spec_ids = request.form.getlist('specialty_ids')
        if spec_ids:
            profile.specialties = Specialty.query.filter(Specialty.id.in_(spec_ids)).all()

        db.session.commit()
        flash('Perfil actualizado.', 'success')
        return redirect(url_for('admin.profiles'))

    return render_template('admin/edit_profile.html', profile=profile,
                           cities=cities, specialties=specialties)


@admin_bp.route('/perfiles/<int:profile_id>/activar', methods=['POST'])
@admin_required
def activate_profile(profile_id):
    from datetime import datetime, timedelta
    profile = Profile.query.get_or_404(profile_id)
    profile.status = 'active'
    profile.subscription_start = datetime.utcnow()
    profile.next_billing_date = datetime.utcnow() + timedelta(days=30)

    payment = Payment.query.filter_by(profile_id=profile_id, status='pending').first()
    if payment:
        payment.status = 'completed'

    db.session.commit()
    flash(f'Perfil "{profile.slug}" activado.', 'success')
    return redirect(url_for('admin.profiles'))


@admin_bp.route('/perfiles/<int:profile_id>/eliminar', methods=['POST'])
@admin_required
def delete_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    force = request.form.get('force') == '1'

    if force:
        db.session.delete(profile)
        db.session.commit()
        flash('Perfil eliminado permanentemente.', 'success')
    else:
        profile.status = 'available'
        profile.user_id = None
        profile.name = None
        profile.description = None
        profile.email = None
        profile.phone = None
        profile.specialties = []
        for img in profile.images:
            db.session.delete(img)
        db.session.commit()
        flash('Perfil reseteado a disponible (URL preservada).', 'info')

    return redirect(url_for('admin.profiles'))


@admin_bp.route('/usuarios')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template('admin/users.html', users=users)


@admin_bp.route('/usuarios/<int:user_id>/admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes modificar tu propio rol.', 'warning')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f'Rol de {user.email} actualizado.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/pagos')
@admin_required
def payments():
    page = request.args.get('page', 1, type=int)
    payments = Payment.query.order_by(Payment.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template('admin/payments.html', payments=payments)
