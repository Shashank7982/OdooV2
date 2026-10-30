import json
import werkzeug
from odoo import http


class PaymentStripeController(http.Controller):
    @http.route('/payment/stripe/create_session', type='http', auth='public', methods=['POST'], csrf=False)
    def create_session(self, **post):
        # Minimal endpoint: expects POST with amount, currency, and return_url
        try:
            amount = int(float(post.get('amount', 0)))
            currency = post.get('currency', 'USD')
            return_url = post.get('return_url') or post.get('success_url') or post.get('cancel_url')
        except Exception:
            return werkzeug.wrappers.Response('Invalid parameters', status=400)

        IrConfig = http.request.env['ir.config_parameter'].sudo()
        secret_key = IrConfig.get_param('payment_stripe.secret_key')
        if not secret_key:
            return werkzeug.wrappers.Response('Stripe secret key not configured', status=500)

        try:
            import stripe
        except Exception:
            return werkzeug.wrappers.Response('Stripe python package is not installed', status=500)

        stripe.api_key = secret_key

        try:
            # amount -> cents for many currencies; caller should provide smallest currency unit if needed
            # Here we assume amount is in major units and convert to cents for common currencies like USD
            unit_amount = int(amount * 100)
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {'name': post.get('description', 'Odoo order')},
                        'unit_amount': unit_amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=post.get('success_url') or return_url or '',
                cancel_url=post.get('cancel_url') or return_url or '',
            )
            return werkzeug.utils.redirect(session.url)
        except Exception as e:
            return werkzeug.wrappers.Response('Stripe error: %s' % (str(e)), status=500)

    @http.route('/payment/stripe/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def webhook(self, **post):
        # Minimal webhook handler: verify signature if set, respond 200
        IrConfig = http.request.env['ir.config_parameter'].sudo()
        secret_key = IrConfig.get_param('payment_stripe.secret_key')
        webhook_secret = IrConfig.get_param('payment_stripe.webhook_secret')
        try:
            import stripe
        except Exception:
            return werkzeug.wrappers.Response('Stripe python package is not installed', status=500)

        payload = http.request.httprequest.get_data()
        sig_header = http.request.httprequest.headers.get('Stripe-Signature')
        event = None
        try:
            if webhook_secret and sig_header:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            else:
                event = json.loads(payload.decode('utf-8'))
        except Exception:
            return werkzeug.wrappers.Response('Invalid webhook payload', status=400)

        # TODO: implement handling of events and reconciling payment.transaction
        # For now, just acknowledge
        return werkzeug.wrappers.Response('ok')
