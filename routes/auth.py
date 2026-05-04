from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Profile
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/registro', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profiles.my_profile'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        if not email or not password or not full_name:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Ya existe una cuenta con ese correo electrónico.', 'danger')
            return render_template('auth/register.html')

        user = User(email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)

        # Handle claim flow from session
        claim_slug = session.pop('claim_slug', None)
        claim_tier = session.pop('claim_tier', 'basico')
        if claim_slug:
            profile = Profile.query.filter_by(slug=claim_slug).first()
            if profile and profile.status == 'available':
                return redirect(url_for('payments.initiate_payment',
                                        profile_id=profile.id,
                                        tier=claim_tier,
                                        payment_type='opening_fee'))

        flash('¡Cuenta creada con éxito! Bienvenido/a.', 'success')
        return redirect(url_for('profiles.new_profile'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profiles.my_profile'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Correo o contraseña incorrectos.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=request.form.get('remember') == 'on')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('profiles.my_profile'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('main.index'))
