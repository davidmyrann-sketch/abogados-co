import os
import stripe
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from models import db, Profile, Payment
from datetime import datetime, timedelta

payments_bp = Blueprint('payments', __name__)

OPENING_FEE = 100
TIER_PRICES = {'basico': 5, 'profesional': 20, 'premium': 35}


@payments_bp.route('/pago/iniciar')
@login_required
def initiate_payment():
    profile_id = request.args.get('profile_id', type=int)
    tier = request.args.get('tier', 'basico')
    payment_type = request.args.get('payment_type', 'opening_fee')

    if tier not in TIER_PRICES:
        tier = 'basico'

    profile = Profile.query.get_or_404(profile_id)

    # Allow claiming if available, or own profile
    if profile.status not in ('available', 'pending_payment'):
        if profile.user_id != current_user.id:
            flash('No tienes permiso para este perfil.', 'danger')
            return redirect(url_for('main.index'))

    stripe_key = current_app.config.get('STRIPE_SECRET_KEY')

    if stripe_key:
        stripe.api_key = stripe_key
        amount = OPENING_FEE * 100  # cents

        tier_labels = {'basico': 'Básico ($5/mes)', 'profesional': 'Profesional ($20/mes)', 'premium': 'Premium ($35/mes)'}

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Apertura perfil — {tier_labels[tier]}',
                            'description': f'Incluye primer mes. URL: losabogados.com.co/bufetes/{profile.slug}'
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=current_app.config['BASE_URL'] + url_for('payments.payment_success',
                                                                       profile_id=profile_id, tier=tier) + '&session_id={CHECKOUT_SESSION_ID}',
                cancel_url=current_app.config['BASE_URL'] + url_for('payments.payment_cancel', profile_id=profile_id),
                customer_email=current_user.email,
                metadata={'profile_id': profile_id, 'tier': tier, 'user_id': current_user.id}
            )

            payment = Payment(
                user_id=current_user.id,
                profile_id=profile_id,
                amount=OPENING_FEE,
                payment_type='opening_fee',
                status='pending',
                stripe_session_id=session.id,
                tier_selected=tier
            )
            db.session.add(payment)
            db.session.commit()

            return redirect(session.url, code=303)

        except Exception as e:
            flash('Error al procesar el pago. Inténtalo de nuevo.', 'danger')
            return redirect(url_for('profiles.profile_detail', slug=profile.slug))

    else:
        # Manual payment mode (no Stripe configured)
        profile.user_id = current_user.id
        profile.tier = tier
        profile.status = 'pending_payment'

        payment = Payment(
            user_id=current_user.id,
            profile_id=profile_id,
            amount=OPENING_FEE,
            payment_type='opening_fee',
            status='pending',
            tier_selected=tier
        )
        db.session.add(payment)
        db.session.commit()

        flash('Tu solicitud ha sido recibida. Un administrador activará tu perfil tras confirmar el pago.', 'info')
        return render_template('payments/manual.html', profile=profile, tier=tier,
                               opening_fee=OPENING_FEE, tier_price=TIER_PRICES[tier])


@payments_bp.route('/pago/exito')
@login_required
def payment_success():
    profile_id = request.args.get('profile_id', type=int)
    tier = request.args.get('tier', 'basico')
    session_id = request.args.get('session_id', '')

    profile = Profile.query.get_or_404(profile_id)

    stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
    if stripe_key and session_id:
        stripe.api_key = stripe_key
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.payment_status == 'paid':
                _activate_profile(profile, tier, current_user.id)
                payment = Payment.query.filter_by(stripe_session_id=session_id).first()
                if payment:
                    payment.status = 'completed'
                db.session.commit()
        except Exception:
            pass

    flash('¡Pago exitoso! Tu perfil ha sido activado.', 'success')
    return render_template('payments/success.html', profile=profile)


@payments_bp.route('/pago/cancelado')
def payment_cancel():
    profile_id = request.args.get('profile_id', type=int)
    profile = Profile.query.get(profile_id)
    flash('El pago fue cancelado.', 'warning')
    if profile:
        return redirect(url_for('profiles.profile_detail', slug=profile.slug))
    return redirect(url_for('main.index'))


@payments_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        if session['payment_status'] == 'paid':
            meta = session.get('metadata', {})
            profile_id = int(meta.get('profile_id', 0))
            tier = meta.get('tier', 'basico')
            user_id = int(meta.get('user_id', 0))

            profile = Profile.query.get(profile_id)
            if profile:
                _activate_profile(profile, tier, user_id)
                payment = Payment.query.filter_by(stripe_session_id=session['id']).first()
                if payment:
                    payment.status = 'completed'
                db.session.commit()

    return jsonify({'status': 'ok'})


def _activate_profile(profile, tier, user_id):
    profile.user_id = user_id
    profile.tier = tier
    profile.status = 'active'
    profile.subscription_start = datetime.utcnow()
    profile.next_billing_date = datetime.utcnow() + timedelta(days=30)
