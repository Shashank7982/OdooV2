import odoo
from odoo import api, SUPERUSER_ID

# Change these values for your Stripe keys
PUBLISHABLE_KEY = 'pk_test_51TpD0l15MX0FtmA0puECO21QMPX9u61Vg35mH4K4x06PC0PdSMi324XDxVL9hbLcG7CpazjODQzzmButcfw13hOZ00mudJYZQX'
SECRET_KEY = 'sk_test_51TpD0l15MX0FtmA07GJEpgZ67J1vTEehl8bAaMxhelkGLw0oRm852gkKZlD2ASLWTdG9mdZVGclhJf5huLJYHOud00zBenAAJo'
WEBHOOK_SECRET = ''

if __name__ == '__main__':
    db_name = 'odoo18db'
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Enable payment_stripe module if not installed
        module = env['ir.module.module'].search([('name', '=', 'payment_stripe')], limit=1)
        if module:
            print('payment_stripe module found:', module.state)
            if module.state != 'installed':
                module.button_immediate_install()
                print('Installed payment_stripe module')
        else:
            print('payment_stripe module not found')

        provider = env['payment.provider'].search([('code', '=', 'stripe')], limit=1)
        if not provider:
            provider = env['payment.provider'].create({
                'name': 'Stripe',
                'code': 'stripe',
                'state': 'enabled',
                'stripe_publishable_key': PUBLISHABLE_KEY,
                'stripe_secret_key': SECRET_KEY,
                'stripe_webhook_secret': WEBHOOK_SECRET,
                'currency_ids': [(6, 0, env['res.currency'].search([('active', '=', True)]).ids)],
                'company_id': env.company.id,
            })
            print('Created Stripe payment provider:', provider.id)
        else:
            provider.write({
                'stripe_publishable_key': PUBLISHABLE_KEY,
                'stripe_secret_key': SECRET_KEY,
                'stripe_webhook_secret': WEBHOOK_SECRET,
                'state': 'enabled',
            })
            print('Updated Stripe payment provider:', provider.id, provider.name)

        # Ensure website payment method configuration exists
        websites = env['website'].search([])
        for website in websites:
            website.payment_method_ids = [(4, provider.id)]
        print('Assigned Stripe provider to websites:', websites.mapped('name'))

        cr.commit()
        print('Done')
