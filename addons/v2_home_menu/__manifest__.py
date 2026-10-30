# -*- coding: utf-8 -*-
{
    'name': 'V2 Home Menu',
    'version': '18.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Beautiful drag-and-drop home dashboard for Odoo 18 Community. Shows on login with live clock, app search, and grid layout.',
    'author': 'Shashank',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'views/home_menu_action.xml',
        'data/home_menu_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'v2_home_menu/static/src/scss/home_menu.scss',
            'v2_home_menu/static/src/xml/home_menu.xml',
            'v2_home_menu/static/src/js/home_menu.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
