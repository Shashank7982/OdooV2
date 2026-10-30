# -*- coding: utf-8 -*-
from odoo import api, models


class MailingMailing(models.Model):
    """Make sure replies to a campaign land back in the same mailbox this
    addon is monitoring: when a confirmed marketing mailbox is configured,
    new mailings default their Reply-To to that mailbox's address instead of
    the current user's personal email.

    This keeps "send" (SMTP, configured on the Outgoing Mail Server using the
    same address) and "receive" (IMAP, configured on the marketing
    `fetchmail.server`) on one single mailbox for this project, which is what
    makes automatic reply/bounce/unsubscribe detection work at all: if
    replies went to a different address than the one being fetched, this
    addon would never see them.
    """
    _inherit = 'mailing.mailing'

    @api.depends('reply_to_mode')
    def _compute_reply_to(self):
        super()._compute_reply_to()
        marketing_email = self.env['fetchmail.server']._mmg_get_marketing_reply_to()
        if not marketing_email:
            return
        for mailing in self:
            if mailing.reply_to_mode == 'new' and (
                not mailing.reply_to or mailing.reply_to == self.env.user.email_formatted
            ):
                mailing.reply_to = marketing_email
