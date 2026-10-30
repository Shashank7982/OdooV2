# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models, tools
from odoo.tools.mail import mail_header_msgid_re

_logger = logging.getLogger(__name__)

UNSUBSCRIBE_HEADERS = ('list-unsubscribe', 'list-unsubscribe-post')


class MarketingInboundMail(models.Model):
    """Audit log of every email fetched from a marketing mailbox.

    This is also the fallback target ('Create a New Record' model) that can be
    configured on a marketing `fetchmail.server`: when an incoming message does
    not thread back to any existing document (lead, mailing trace, ...) Odoo's
    mail gateway creates a record here through :meth:`message_new` instead of
    silently dropping it.
    """
    _name = 'marketing.inbound.mail'
    _description = 'Marketing Inbound Mail'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'subject'

    subject = fields.Char(string='Subject')
    email_from = fields.Char(string='From', index=True)
    email_to = fields.Char(string='To')
    message_id = fields.Char(string='Message-Id', index=True, copy=False)
    in_reply_to = fields.Char(string='In-Reply-To')
    received_date = fields.Datetime(string='Received On', default=fields.Datetime.now)
    body = fields.Html(string='Body')
    body_preview = fields.Char(string='Message Preview', compute='_compute_body_preview', store=True)

    category = fields.Selection([
        ('reply', 'Reply'),
        ('bounce', 'Bounce'),
        ('unsubscribe', 'Unsubscribe Request'),
        ('other', 'Other'),
    ], string='Category', default='other', required=True, index=True)
    state = fields.Selection([
        ('new', 'New'),
        ('processed', 'Processed'),
        ('duplicate', 'Duplicate'),
        ('error', 'Error'),
    ], string='Status', default='new', required=True, index=True, copy=False)
    error_message = fields.Text(string='Error')

    fetchmail_server_id = fields.Many2one('fetchmail.server', string='Mail Server', readonly=True)
    mailing_trace_id = fields.Many2one('mailing.trace', string='Mailing Trace', readonly=True)
    mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing', readonly=True)
    campaign_id = fields.Many2one('utm.campaign', string='Campaign', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contact')
    mailing_contact_id = fields.Many2one('mailing.contact', string='Mailing Contact', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='CRM Lead / Opportunity', readonly=True)
    related_res_model = fields.Char(string='Related Document Model', readonly=True)
    related_res_id = fields.Many2oneReference(string='Related Document Id', model_field='related_res_model', readonly=True)

    _sql_constraints = [
        ('message_id_unique', 'unique(message_id)',
         'This email (Message-Id) has already been logged: duplicate messages are ignored.'),
    ]

    @api.depends('body')
    def _compute_body_preview(self):
        for log in self:
            plain = tools.html2plaintext(log.body or '').strip()
            plain = ' '.join(plain.split())  # collapse newlines/whitespace for a one-line snippet
            log.body_preview = (plain[:140] + '…') if len(plain) > 140 else plain

    # ------------------------------------------------------------
    # Classification helpers - reused by both the message_new fallback
    # and the mail.thread routing hook (models/mail_thread.py)
    # ------------------------------------------------------------

    @api.model
    def _mmg_extract_references(self, message_dict):
        thread_references = message_dict.get('references') or message_dict.get('in_reply_to') or ''
        return mail_header_msgid_re.findall(thread_references)

    @api.model
    def _mmg_find_trace(self, message_dict):
        msg_references = self._mmg_extract_references(message_dict)
        if not msg_references:
            return self.env['mailing.trace']
        return self.env['mailing.trace'].sudo().search(
            [('message_id', 'in', msg_references)], limit=1)

    @api.model
    def _mmg_classify(self, message, message_dict, server=None):
        """Return the best-guess category ('bounce', 'unsubscribe', 'reply' or 'other')
        for an incoming email, without touching the database."""
        if message_dict.get('is_bounce') or message_dict.get('bounced_email') or message_dict.get('bounced_msg_ids'):
            return 'bounce'

        keywords = []
        if server and server.marketing_unsubscribe_keywords:
            keywords = [kw.strip().lower() for kw in server.marketing_unsubscribe_keywords.split(',') if kw.strip()]

        if message is not None:
            for header in UNSUBSCRIBE_HEADERS:
                if message.get(header):
                    return 'unsubscribe'

        subject = (message_dict.get('subject') or '').lower()
        body = tools.html2plaintext(message_dict.get('body') or '').lower()
        haystack = f'{subject}\n{body}'
        if keywords and any(kw in haystack for kw in keywords):
            return 'unsubscribe'

        if self._mmg_find_trace(message_dict):
            return 'reply'

        return 'other'

    @api.model
    def _mmg_prepare_log_values(self, message, message_dict, server=None, category=None):
        trace = self._mmg_find_trace(message_dict)
        email_from = message_dict.get('email_from')
        partner = self.env['res.partner']
        mailing_contact = self.env['mailing.contact']
        lead = self.env['crm.lead']
        related_res_model = False
        related_res_id = False

        if trace:
            related_res_model = trace.model
            related_res_id = trace.res_id
            if trace.model == 'crm.lead':
                lead = self.env['crm.lead'].sudo().browse(trace.res_id).exists()
                partner = lead.partner_id
            elif trace.model == 'mailing.contact':
                mailing_contact = self.env['mailing.contact'].sudo().browse(trace.res_id).exists()

        if not partner and email_from:
            normalized = tools.email_normalize(email_from)
            if normalized:
                partner = self.env['res.partner'].sudo().search(
                    [('email_normalized', '=', normalized)], limit=1)

        return {
            'subject': message_dict.get('subject'),
            'email_from': email_from,
            'email_to': message_dict.get('to'),
            'message_id': message_dict.get('message_id'),
            'in_reply_to': message_dict.get('in_reply_to'),
            'body': message_dict.get('body'),
            'category': category or self._mmg_classify(message, message_dict, server=server),
            'state': 'new',
            'fetchmail_server_id': server.id if server else False,
            'mailing_trace_id': trace.id if trace else False,
            'mailing_id': trace.mass_mailing_id.id if trace else False,
            'campaign_id': trace.campaign_id.id if trace else False,
            'partner_id': partner.id if partner else False,
            'mailing_contact_id': mailing_contact.id if mailing_contact else False,
            'lead_id': lead.id if lead else False,
            'related_res_model': related_res_model,
            'related_res_id': related_res_id,
        }

    # ------------------------------------------------------------
    # Processing (bounce marking / unsubscribe / lead update)
    # ------------------------------------------------------------

    def action_retry_processing(self):
        return self._mmg_process()

    def _mmg_process(self):
        """Apply the side effects (blacklist, list opt-out, trace update, lead
        activity) for logged messages still in the 'new' state. Idempotent and
        safe to call multiple times (e.g. from the retry cron)."""
        for log in self.filtered(lambda l: l.state in ('new', 'error')):
            try:
                if log.category == 'unsubscribe':
                    log._mmg_process_unsubscribe()
                elif log.category == 'bounce' and log.mailing_trace_id:
                    log.mailing_trace_id.set_bounced(
                        bounce_message=tools.html2plaintext(log.body or ''))
                elif log.category == 'reply' and log.lead_id:
                    log.lead_id.message_post(
                        body=_("New reply received in the marketing mailbox from %s.", log.email_from),
                        subtype_xmlid='mail.mt_note')
                log.state = 'processed'
                log.error_message = False
            except Exception as exc:  # noqa: BLE001 - log & continue, never blocks the gateway
                _logger.exception('Failed to process marketing inbound mail %s', log.id)
                log.write({'state': 'error', 'error_message': str(exc)})
        return True

    def _mmg_process_unsubscribe(self):
        self.ensure_one()
        email = tools.email_normalize(self.email_from) or self.email_from
        if not email:
            return
        if self.mailing_contact_id and self.mailing_id and self.mailing_id.contact_list_ids:
            subscriptions = self.env['mailing.subscription'].sudo().search([
                ('contact_id', '=', self.mailing_contact_id.id),
                ('list_id', 'in', self.mailing_id.contact_list_ids.ids),
            ])
            if subscriptions:
                subscriptions.write({'opt_out': True})
            else:
                self.mailing_contact_id.opt_out = True
        self.env['mail.blacklist'].sudo()._add(
            email,
            message=_('Automatically blocklisted: unsubscribe request received on %s.', self.received_date))
        if self.partner_id:
            self.partner_id.message_post(
                body=_("This contact requested to unsubscribe via the marketing mailbox."))

    @api.model
    def _mmg_log_routed_message(self, message, message_dict, server):
        """Log a message that the mail gateway threaded to an existing
        document (e.g. a reply posted on a crm.lead's chatter) instead of
        going through :meth:`message_new`. Never raises: logging must not
        block normal mail gateway processing."""
        message_id = message_dict.get('message_id')
        if not message_id:
            return self.browse()
        if self.sudo().search_count([('message_id', '=', message_id)], limit=1):
            return self.browse()
        try:
            values = self._mmg_prepare_log_values(message, message_dict, server=server)
            values['fetchmail_server_id'] = server.id
            log = self.sudo().create(values)
            log._mmg_process()
            return log
        except Exception:  # noqa: BLE001
            _logger.exception('Failed to log routed marketing inbound mail %s', message_id)
            return self.browse()

    # ------------------------------------------------------------
    # mail.thread override: fallback target for un-threaded messages
    # ------------------------------------------------------------

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        server = self.env['fetchmail.server'].browse(self.env.context.get('default_fetchmail_server_id'))
        server = server.exists()

        msg_id = msg_dict.get('message_id')
        existing = self.env['marketing.inbound.mail'].sudo().search(
            [('message_id', '=', msg_id)], limit=1) if msg_id else self.browse()
        if existing:
            return existing

        values = self._mmg_prepare_log_values(None, msg_dict, server=server)
        if custom_values:
            values.update(custom_values)
        record = super(MarketingInboundMail, self).message_new(msg_dict, custom_values=values)
        record._mmg_process()
        return record
