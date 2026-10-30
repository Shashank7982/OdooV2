{
    'name': 'Website Sale Affiliate (OCA Base)',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Base module to track affiliate links and associate them with sales orders.',
    'author': 'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/e-commerce',
    'license': 'LGPL-3',
    # V2 intentionally removes the Website/eCommerce application. Affiliate
    # tracking and accounting can still operate against Sales orders.
    'depends': ['sale'],
    'data': [],
    'installable': True,
}
