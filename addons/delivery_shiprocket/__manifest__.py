# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Shiprocket Shipping',
    'category': 'Inventory/Delivery',
    'summary': 'Send your shipments through Shiprocket and track them online',
    'description': """
Shiprocket Integration
=======================
This module allows you to generate shipments with Shiprocket, get real-time
rate estimates, generate shipping labels/AWB and track deliveries directly
from Odoo.

Configuration
-------------
1. Create a Shiprocket account at https://app.shiprocket.in
2. Go to Inventory / Sales > Configuration > Delivery > Shipping Methods
3. Create a new Shipping Method, set Provider to "Shiprocket"
4. Enter your Shiprocket account email/password and pickup location details
""",
    'version': '1.0',
    'depends': ['delivery', 'stock_delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_shiprocket_views.xml',
        'views/stock_picking_views.xml',
        'data/shiprocket_cron.xml',
    ],
    'license': 'LGPL-3',
}
