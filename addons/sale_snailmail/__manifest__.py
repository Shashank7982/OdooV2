# -*- coding: utf-8 -*-
{
    'name': "Send Sales Orders by Post",
    'summary': "Send a confirmed sales order by post (Snail Mail), from the backend or the customer portal.",
    'description': """
Adds a "Send by Post" action on sale.order, independent of the Accounting/Invoicing
app: staff can trigger it from the order form, and customers can request a printed
copy of their own confirmed order from the customer portal.
    """,
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale', 'snailmail', 'portal'],
    'data': [
        'views/sale_order_views.xml',
        'views/sale_portal_templates.xml',
    ],
    'license': 'LGPL-3',
}
