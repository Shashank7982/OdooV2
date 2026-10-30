{
    'name': 'Custom Accounting Core',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Core accounting hardening: shared validation, audit metadata, balanced-entry enforcement, idempotent cron moves, period-lock enforcement.',
    'depends': ['account', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/validation_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}