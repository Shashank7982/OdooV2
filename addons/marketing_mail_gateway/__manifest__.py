# -*- coding: utf-8 -*-
{
    'name': 'Marketing Mail Gateway',
    'version': '18.0.1.0.0',
    'category': 'Marketing/Email Marketing',
    'summary': 'IMAP/POP3 incoming mail processing for marketing replies, bounces and unsubscribe requests',
    'description': """
Marketing Mail Gateway
=======================
Connects a marketing mailbox (IMAP, with optional POP3 fallback) to Odoo using
the standard `fetchmail.server` gateway and links every incoming email to the
originating mass mailing campaign, contact and/or CRM lead.

Features
--------
* Reuses Odoo's built-in mail gateway (`fetchmail.server` / `mail.thread.message_process`)
  instead of re-implementing IMAP/POP3 handling.
* Classifies incoming mail as reply / bounce / unsubscribe request / other.
* Links every message to the `mailing.trace`, `utm.campaign`, `res.partner`
  and `crm.lead` it relates to, when it can be determined.
* Automatically opts contacts out of the relevant mailing list (or the global
  blocklist) when an unsubscribe request is detected.
* Keeps a searchable, auditable log (`marketing.inbound.mail`) of every
  message processed, with deduplication on the email Message-Id.
* Automated retry of failed messages through a scheduled action.
""",
    'author': 'Odoo Custom Development',
    'license': 'LGPL-3',
    'depends': ['mail', 'mass_mailing', 'crm'],
    'data': [
        'security/marketing_mail_gateway_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/marketing_inbound_mail_views.xml',
        'views/fetchmail_server_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
