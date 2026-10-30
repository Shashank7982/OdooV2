{
    'name': 'Indiamart CRM Connector',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Pull Indiamart Lead Manager inquiries into Odoo CRM leads',
    'description': """
Indiamart CRM Connector
========================
Polls Indiamart's Lead Manager (Pull) API on a schedule and creates/updates
CRM leads in Odoo, deduplicated by Indiamart's unique query id.

Requires an Indiamart CRM key from a paid seller account
(Indiamart seller panel > Lead Manager > CRM Integration).
""",
    'depends': ['crm'],
    'data': [
        'data/utm_source_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
