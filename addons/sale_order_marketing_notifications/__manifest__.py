{
    'name': 'Sale/Payment Notifications via Marketing SMTP',
    'category': 'Sales/Sales',
    'summary': 'Auto-send order confirmation & payment-due emails through the dedicated marketing SMTP relay',
    'description': """
Sale/Payment Notifications via Marketing SMTP
================================================
Two things, both driven off the outgoing mail server already reserved for
email marketing (Brevo SMTP — see EMAIL_DOMAIN_MIGRATION_README.md, "Gmail
SMTP isn't the right long-term tool for marketing mail"), so transactional
customer notifications don't compete with/pollute the personal or bulk
mailboxes:

1. Order confirmation email now sends automatically the moment a sales
   order is confirmed from the backend (not only when using the "Send by
   Email" wizard) — routed through that same SMTP relay.
2. The existing overdue-payment follow-up email (custom_accounting_followup)
   is pointed at the same SMTP relay.

Does not add a new mail server — it looks up the existing one (identified by
its SMTP host containing "brevo") at install time and assigns it as the
mail_server_id on the two mail.template records used for these emails. If no
such server is found, install proceeds but templates keep using the default
server selection (lowest sequence) as before.
""",
    'version': '1.0',
    'depends': ['sale', 'account', 'custom_accounting_followup'],
    'post_init_hook': 'post_init_hook',
    'data': [],
    'license': 'LGPL-3',
}
