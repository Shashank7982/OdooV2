import odoo
from odoo import api, SUPERUSER_ID

DB_NAME = 'odoo18db'
registry = odoo.registry(DB_NAME)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    print('website model fields')
    website = env['website']
    website_fields = sorted(website._fields.keys())
    for field in website_fields:
        if 'payment' in field or 'payment' in website._fields[field].string.lower():
            print(field, website._fields[field], website._fields[field].string)

    print('\npayment.provider fields')
    provider = env['payment.provider']
    provider_fields = sorted(provider._fields.keys())
    for field in provider_fields:
        if 'website' in field or 'stripe' in field or 'payment' in field:
            print(field, provider._fields[field], provider._fields[field].string)

    stripe_module = env['ir.module.module'].search([('name', '=', 'payment_stripe')], limit=1)
    print('\npayment_stripe module', stripe_module and stripe_module.state)
    stripe_provider = env['payment.provider'].search([('code', '=', 'stripe')], limit=1)
    print('stripe provider count', len(stripe_provider))
    if stripe_provider:
        print('stripe provider state', stripe_provider.state)
        print('stripe provider publishable', stripe_provider.stripe_publishable_key)
        print('stripe provider secret set', bool(stripe_provider.stripe_secret_key))
    print('\nwebsite count', env['website'].search_count([]))
    for website in env['website'].search([]):
        print('website', website.id, website.name, website.sudo().mapped('payment_*'))
    print('done')
