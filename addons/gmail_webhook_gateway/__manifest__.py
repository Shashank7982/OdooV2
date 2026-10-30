# -*- coding: utf-8 -*-
{
    'name': 'Gmail Webhook Gateway',
    'version': '18.0.1.0.0',
    'category': 'Discuss',
    'summary': 'Real-time inbound Gmail processing via Gmail API + Cloud Pub/Sub push (no IMAP polling)',
    'description': """
Gmail Webhook Gateway
======================
Replaces IMAP polling (`fetchmail.server`) with a push-based pipeline for a
single Gmail mailbox: Gmail API `watch()` + Google Cloud Pub/Sub push
notifications deliver new-mail events to Odoo in near real time instead of
waiting for the next cron tick.

How it works
------------
* One `gmail.webhook.account` record holds the OAuth2 app credentials, the
  authorized mailbox's tokens, and the Pub/Sub topic to watch.
* Google pushes a lightweight change notification (just a new `historyId`,
  no email content) to a per-account, secret-token-protected webhook URL.
* The controller fetches the actual new message(s) via the Gmail API
  (`history.list` + `messages.get`, format=raw) and hands the raw RFC822
  bytes to Odoo's standard `mail.thread.message_process()` - the exact same
  entry point `fetchmail.server` uses, so all existing routing/classification
  logic (bounce/unsubscribe/reply detection, thread matching, etc.) is reused
  unchanged.
* A daily cron renews the Gmail `watch()` registration, which Google expires
  after at most 7 days.
* When a new message is processed, an in-app toast notification (Odoo's bus)
  is sent to the account's configured notification users, so nobody has to
  refresh or wait on a cron to see that mail arrived.

Setup (see README.md for the full walkthrough)
------------------------------------------------
1. Create a Google Cloud project, enable the Gmail API and Cloud Pub/Sub API.
2. Create a Pub/Sub topic and a push subscription pointing at this instance's
   public HTTPS webhook URL (shown on the account form once saved).
3. Grant `gmail-api-push@system.gserviceaccount.com` publish rights on the topic.
4. Create OAuth2 Client ID/Secret credentials (type: Web application).
5. Fill in a `gmail.webhook.account` record with those values and click
   "Connect Gmail Account" to complete the OAuth2 consent flow, then
   "Start Watching" to register the mailbox.
""",
    'author': 'Odoo Custom Development',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'security/gmail_webhook_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/gmail_webhook_account_views.xml',
        'views/templates.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
