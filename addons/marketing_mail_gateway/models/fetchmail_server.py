# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools import email_normalize


class FetchmailServer(models.Model):
    """Extend the standard mail gateway configuration so a mailbox can be
    flagged as the marketing inbox (replies / bounces / unsubscribe requests).

    No core behaviour is changed: fetching, cron scheduling and IMAP/POP3
    connection handling are entirely reused from `mail.fetchmail.server`.
    """
    _inherit = 'fetchmail.server'

    is_marketing_mailbox = fields.Boolean(
        string='Marketing Mailbox',
        help="Mark this mailbox as dedicated to marketing replies, bounces and "
             "unsubscribe requests. Every message fetched from it is logged and "
             "linked to the related campaign, contact or lead. For reply "
             "detection to work, outgoing marketing emails must be sent FROM "
             "this same address (see the Outgoing Mail Server Match below).")
    marketing_unsubscribe_keywords = fields.Char(
        string='Unsubscribe Keywords',
        default='unsubscribe,remove me,stop sending,opt out,opt-out,se desabonner,désabonner',
        help="Comma separated list of keywords used, in addition to the "
             "List-Unsubscribe header, to detect unsubscribe requests in the "
             "subject or body of an incoming email.")
    outgoing_match_status = fields.Char(
        string='Outgoing Mail Server Match', compute='_compute_outgoing_match_status',
        help="Whether an Outgoing Mail Server using this same address as login "
             "was found. Sending and receiving must use the same mailbox for "
             "replies to be detected.")

    @api.depends('is_marketing_mailbox', 'user')
    def _compute_outgoing_match_status(self):
        for server in self:
            if not server.is_marketing_mailbox:
                server.outgoing_match_status = False
                continue
            normalized = email_normalize(server.user or '')
            if not normalized:
                server.outgoing_match_status = _('Set a Username (email address) to check.')
                continue
            match = self.env['ir.mail_server'].sudo().search(
                [('smtp_user', '!=', False)]).filtered(
                    lambda s, normalized=normalized: email_normalize(s.smtp_user) == normalized)
            if match:
                server.outgoing_match_status = _('OK: matches Outgoing Mail Server "%s".', match[0].name)
            else:
                server.outgoing_match_status = _(
                    'Warning: no Outgoing Mail Server logs in as %s. Replies will not be '
                    'detected unless marketing emails are actually sent FROM this address.',
                    server.user)

    @api.model
    def _mmg_get_marketing_reply_to(self):
        """Return "Name <email>" for the confirmed marketing mailbox, if any,
        so outgoing marketing emails (mailing.mailing) can default their
        Reply-To to the exact address this addon is fetching from."""
        server = self.sudo().search(
            [('is_marketing_mailbox', '=', True), ('state', '=', 'done'), ('user', '!=', False)],
            limit=1)
        if not server or not email_normalize(server.user):
            return False
        return '%s <%s>' % (server.name, server.user)
