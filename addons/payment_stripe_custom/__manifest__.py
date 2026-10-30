{
    'name': 'Payment Stripe Custom',
    'version': '1.0.0',
    'summary': 'Stripe payment integration (minimal)',
    'category': 'Accounting/Payment',
    'author': 'You',
    'website': 'https://example.com',
    'license': 'AGPL-3',
    'depends': ['payment', 'website'],
    'data': [
        'views/payment_stripe_config_view.xml',
    ],
    'installable': True,
    'application': False,
}
