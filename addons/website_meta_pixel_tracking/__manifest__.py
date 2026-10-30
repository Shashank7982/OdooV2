{
    'name': 'Meta Pixel Tracking',
    'category': 'Website',
    'summary': 'Install Meta Pixel on your Odoo website and log page views, purchases and leads for reporting',
    'description': """
Meta Pixel Tracking
====================
Injects the Meta (Facebook) Pixel base code into every page of your Odoo
website and fires standard events:

- PageView on every page (client-side, via the Pixel)
- Purchase on the eCommerce order confirmation page (client-side Pixel event
  + a server-side record for in-Odoo reporting)
- Lead when a website form (e.g. Contact Us) successfully creates a CRM lead
  (client-side Pixel event + a server-side record)

A "Meta Pixel Events" log inside Odoo lets you see traffic/conversion trends
without leaving Odoo, in addition to what shows up in Meta Events Manager.

Configuration
-------------
Website > Configuration > Settings > Meta Pixel Tracking: enter your Pixel ID.
""",
    'version': '1.0',
    'depends': ['website', 'website_sale', 'website_crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/website_templates.xml',
        'views/res_config_settings_views.xml',
        'views/meta_pixel_event_views.xml',
    ],
    'license': 'LGPL-3',
}
