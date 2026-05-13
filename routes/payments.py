import stripe
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from models import db, Profile, Payment
from datetime import datetime, timedelta

payments_bp = Blueprint('payments', __name__)

MONTHLY_PRICE = 40  # USD


def _get_or_create_stripe_price():
    """Hent Stripe Price ID fra env, eller opprett én gang."""
    price_id = current_app.config.get('STRIPE_PRICE_ID')
    if price_id:
        return price_id
    # Opprett produkt + pris første gang
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    product = stripe.Product.create(name='Abogadoya.com.co — Perfil de abogado', url='https://abogadoya.com.co')
    price = stripe.Price.create(
        unit_amount=MONTHLY_PRICE * 100,
        currency='usd',
        recurring={'interval': 'month'},
        product=product.id,
    )
    return price.id


@payments_bp.route('/suscribirse/<int:profile_id>')
@login_required
def start_subscription(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        flash('No tienes permiso para este perfil.', 'danger')
        return redirect(url_for('main.index'))

    stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
    base_url = current_app.config.get('BASE_URL', 'https://abogadoya.com.co')

    if not stripe_key:
        # Sin Stripe — activación manual
        profile.status = 'pending_payment'
        db.session.commit()
        flash('Tu solicitud ha sido recibida. Un administrador activará tu perfil tras confirmar el pago.', 'info')
        return render_template('payments/manual.html', profile=profile, monthly_price=MONTHLY_PRICE)

    stripe.api_key = stripe_key
    try:
        price_id = _get_or_create_stripe_price()

        # Crea o recupera customer de Stripe
        customer_id = profile.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(email=current_user.email, name=profile.name or current_user.full_name)
            customer_id = customer.id
            profile.stripe_customer_id = customer_id
            db.session.commit()

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=base_url + url_for('payments.subscription_success', profile_id=profile_id) + '&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base_url + url_for('payments.subscription_cancel', profile_id=profile_id),
            metadata={'profile_id': profile_id, 'user_id': current_user.id},
            subscription_data={'metadata': {'profile_id': profile_id}},
        )
        return redirect(session.url, code=303)

    except Exception as e:
        flash('Error al procesar el pago. Inténtalo de nuevo.', 'danger')
        return redirect(url_for('profiles.my_profile'))


@payments_bp.route('/suscripcion/exito')
@login_required
def subscription_success():
    profile_id = request.args.get('profile_id', type=int)
    session_id = request.args.get('session_id', '')
    profile = Profile.query.get_or_404(profile_id)

    stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
    if stripe_key and session_id:
        stripe.api_key = stripe_key
        try:
            checkout = stripe.checkout.Session.retrieve(session_id)
            sub = stripe.Subscription.retrieve(checkout.subscription)
            profile.stripe_subscription_id = sub.id
            profile.status = 'active'
            profile.subscription_start = datetime.utcnow()
            profile.next_billing_date = datetime.utcnow() + timedelta(days=30)
            payment = Payment(
                user_id=current_user.id,
                profile_id=profile_id,
                amount=MONTHLY_PRICE,
                payment_type='subscription',
                status='completed',
                stripe_session_id=session_id,
            )
            db.session.add(payment)
            db.session.commit()
        except Exception:
            pass

    flash('¡Suscripción activada! Tu perfil ya está en línea.', 'success')
    return render_template('payments/success.html', profile=profile)


@payments_bp.route('/suscripcion/cancelar/<int:profile_id>', methods=['POST'])
@login_required
def cancel_subscription(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        flash('No tienes permiso.', 'danger')
        return redirect(url_for('main.index'))

    stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
    if stripe_key and profile.stripe_subscription_id:
        stripe.api_key = stripe_key
        try:
            # Cancela al final del período — 1 mes de aviso
            stripe.Subscription.modify(profile.stripe_subscription_id, cancel_at_period_end=True)
            profile.cancel_at_period_end = True
            profile.cancelled_at = datetime.utcnow()
            db.session.commit()
            flash('Tu suscripción se cancelará al final del período de facturación actual. Tu perfil seguirá activo hasta entonces.', 'info')
        except Exception as e:
            flash('Error al cancelar. Contáctanos en soporte@abogadoya.com.co', 'danger')
    else:
        profile.status = 'cancelled'
        profile.cancelled_at = datetime.utcnow()
        db.session.commit()
        flash('Tu suscripción ha sido cancelada.', 'info')

    return redirect(url_for('profiles.my_profile'))


@payments_bp.route('/suscripcion/cancelado')
def subscription_cancel():
    profile_id = request.args.get('profile_id', type=int)
    flash('El pago fue cancelado. Puedes intentarlo de nuevo cuando quieras.', 'warning')
    return redirect(url_for('profiles.my_profile'))


@payments_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'invoice.paid':
        sub_id = event['data']['object'].get('subscription')
        profile = Profile.query.filter_by(stripe_subscription_id=sub_id).first()
        if profile:
            profile.status = 'active'
            profile.next_billing_date = datetime.utcnow() + timedelta(days=30)
            db.session.commit()

    elif event['type'] in ('customer.subscription.deleted', 'invoice.payment_failed'):
        sub_id = event['data']['object'].get('id') or event['data']['object'].get('subscription')
        profile = Profile.query.filter_by(stripe_subscription_id=sub_id).first()
        if profile:
            profile.status = 'inactive'
            db.session.commit()

    return jsonify({'status': 'ok'})
