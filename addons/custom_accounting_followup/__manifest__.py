{
    'name': 'Custom Accounting Follow-up',
    'category': 'Accounting/Accounting',
    'summary': 'Overdue invoice follow-up levels, reminder emails, and activities',
    'description': """
Custom Accounting Follow-up
===============================
Part of custom_full_accounting. Built from scratch (Enterprise's
account_followup is not present in this Community instance).

- Configurable follow-up levels (days overdue -> action: email / activity)
- A daily cron scans overdue customer invoices, determines each partner's
  current follow-up level, and triggers the configured action
- Manual "Send Follow-up Now" action from a partner or invoice
- Follow-up history logged to the partner's chatter
""",
    'version': '1.0',
    'depends': ['account', 'mail', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/followup_level_data.xml',
        'views/account_followup_level_views.xml',
        'views/res_partner_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
