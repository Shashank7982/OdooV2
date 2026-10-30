# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Display Working Hours in Calendar",
    'version': '1.0',
    'category': 'Human Resources/Employees',
    # Calendar must remain available in V2 even though Employees is removed.
    'depends': ['calendar'],
    'auto_install': True,
    'data': [
        'views/calendar_views_calendarApp.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_calendar/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr_calendar/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
