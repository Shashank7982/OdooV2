# -*- coding: utf-8 -*-
import time
from random import randint

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged

MAIL_TEMPLATE = """Return-Path: {return_path}
To: {to}
cc: {cc}
Received: by mail1.example.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}

{body}
"""


@tagged('post_install', '-at_install')
class TestMarketingInboundMail(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = cls.env['fetchmail.server'].create({
            'name': 'Marketing Inbox',
            'server_type': 'imap',
            'server': 'imap.example.com',
            'is_marketing_mailbox': True,
            'object_id': cls.env['ir.model']._get_id('marketing.inbound.mail'),
        })
        cls.campaign = cls.env['utm.campaign'].create({'name': 'Test Campaign'})
        cls.mailing = cls.env['mailing.mailing'].create({
            'subject': 'Test Mailing',
            'campaign_id': cls.campaign.id,
            'mailing_model_id': cls.env['ir.model']._get_id('crm.lead'),
        })
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Test Lead',
            'email_from': 'lead.contact@customer.example.com',
        })
        cls.trace = cls.env['mailing.trace'].create({
            'mass_mailing_id': cls.mailing.id,
            'model': 'crm.lead',
            'res_id': cls.lead.id,
            'message_id': '<original-campaign-message@example.com>',
            'email': 'lead.contact@customer.example.com',
            'trace_status': 'sent',
        })

    def _process(self, email_from, subject, extra='', body='Hello', msg_id=None):
        msg_id = msg_id or "<%.7f-%05d-test@iron.sky>" % (time.time(), randint(0, 99998))
        mail = MAIL_TEMPLATE.format(
            return_path='<bounce@example.com>',
            to='marketing@example.com', cc='',
            email_from=email_from, subject=subject,
            extra=extra, msg_id=msg_id, body=body,
        )
        self.env['mail.thread'].sudo().with_context(
            default_fetchmail_server_id=self.server.id,
        ).message_process('marketing.inbound.mail', mail)
        return msg_id

    def test_reply_links_lead_and_campaign(self):
        """A reply threaded via References to a mailing.trace must be logged
        and linked to the originating lead and campaign."""
        msg_id = self._process(
            'lead.contact@customer.example.com', 'Re: Test Mailing',
            extra='References: <original-campaign-message@example.com>\n',
            body='I am interested, please call me back.',
        )
        log = self.env['marketing.inbound.mail'].search([('message_id', '=', msg_id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.category, 'reply')
        self.assertEqual(log.state, 'processed')
        self.assertEqual(log.lead_id, self.lead)
        self.assertEqual(log.campaign_id, self.campaign)
        self.assertEqual(self.trace.trace_status, 'reply')

    def test_bounce_detected_and_trace_updated(self):
        """An email from mailer-daemon referencing the campaign message must
        be classified as a bounce and update the mailing trace."""
        msg_id = self._process(
            'mailer-daemon@example.com', 'Undelivered Mail Returned to Sender',
            extra='References: <original-campaign-message@example.com>\n',
            body='550 no such user',
        )
        log = self.env['marketing.inbound.mail'].search([('message_id', '=', msg_id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.category, 'bounce')
        self.assertEqual(log.state, 'processed')
        self.assertEqual(self.trace.trace_status, 'bounce')

    def test_unsubscribe_keyword_blacklists_contact(self):
        """A message whose subject contains an unsubscribe keyword must be
        classified accordingly and blacklist the sender."""
        email = 'unhappy.customer@customer.example.com'
        msg_id = self._process(email, 'Please unsubscribe me from this list')
        log = self.env['marketing.inbound.mail'].search([('message_id', '=', msg_id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.category, 'unsubscribe')
        self.assertEqual(log.state, 'processed')
        blacklist_entry = self.env['mail.blacklist'].sudo().search([('email', '=', email)])
        self.assertEqual(len(blacklist_entry), 1)

    def test_duplicate_message_id_is_ignored(self):
        """Processing the same Message-Id twice must not create two log
        entries (deduplication)."""
        msg_id = '<duplicate-test@example.com>'
        self._process('someone@customer.example.com', 'Hello there', msg_id=msg_id)
        self._process('someone@customer.example.com', 'Hello there', msg_id=msg_id)
        logs = self.env['marketing.inbound.mail'].search([('message_id', '=', msg_id)])
        self.assertEqual(len(logs), 1)

    def test_non_marketing_server_not_logged(self):
        """Messages fetched from a mailbox not flagged as marketing must not
        be logged by this module."""
        other_server = self.env['fetchmail.server'].create({
            'name': 'Support Inbox',
            'server_type': 'imap',
            'server': 'imap.example.com',
            'is_marketing_mailbox': False,
        })
        msg_id = "<%.7f-%05d-test@iron.sky>" % (time.time(), randint(0, 99998))
        mail = MAIL_TEMPLATE.format(
            return_path='<bounce@example.com>', to='support@example.com', cc='',
            email_from='lead.contact@customer.example.com', subject='Re: Test Mailing',
            extra='References: <original-campaign-message@example.com>\n',
            msg_id=msg_id, body='hello',
        )
        self.env['mail.thread'].sudo().with_context(
            default_fetchmail_server_id=other_server.id,
        ).message_process('crm.lead', mail)
        log = self.env['marketing.inbound.mail'].search([('message_id', '=', msg_id)])
        self.assertFalse(log)
