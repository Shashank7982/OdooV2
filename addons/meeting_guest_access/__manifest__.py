{
    'name': 'Discuss Secure Meeting Guest Access',
    'version': '1.0.0',
    'category': 'Productivity/Discuss',
    'depends': ['mail', 'base_setup'],
    'data': [
        'views/meeting_join_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'meeting_guest_access/static/src/js/meeting_credentials.js',
            'meeting_guest_access/static/src/xml/meeting_credentials.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
