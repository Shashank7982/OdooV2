# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'iThink Logistics Shipping',
    'category': 'Inventory/Delivery',
    'summary': 'Send your shipments through iThink Logistics and track them online',
    'description': """
iThink Logistics Integration
=============================
This module allows you to generate shipments with iThink Logistics, get
real-time rate estimates, generate shipping labels/manifest and track
deliveries directly from Odoo.

Configuration
-------------
1. Get your Access Token and Secret Key from iThink Logistics
   (https://www.ithinklogistics.com).
2. Go to Inventory / Sales > Configuration > Delivery > Shipping Methods.
3. Create a new Shipping Method, set Provider to "iThink Logistics".
4. Enter your Access Token, Secret Key and pickup address ID.
""",
    'version': '1.0',
    'depends': ['delivery', 'stock_delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_ithink_views.xml',
        'views/stock_picking_views.xml',
        'data/ithink_cron.xml',
    ],
    'license': 'LGPL-3',
}
