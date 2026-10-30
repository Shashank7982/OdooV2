# -*- coding: utf-8 -*-
from odoo import api, models


class MailThread(models.AbstractModel):
    """Log every message fetched from a marketing mailbox, even when the mail
    gateway threads it back to an existing document (e.g. a reply attached to
    a CRM lead's chatter) instead of falling back to `message_new`.
    """
    _inherit = 'mail.thread'

    def _mmg_get_marketing_server(self):
        server_id = self.env.context.get('default_fetchmail_server_id')
        if not server_id:
            return self.env['fetchmail.server']
        server = self.env['fetchmail.server'].browse(server_id).exists()
        return server if server and server.is_marketing_mailbox else self.env['fetchmail.server']

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        server = self._mmg_get_marketing_server()
        if server and routes:
            self.env['marketing.inbound.mail']._mmg_log_routed_message(message, message_dict, server)
        return super()._message_route_process(message, message_dict, routes)

    @api.model
    def _routing_handle_bounce(self, email_message, message_dict):
        # Bounce emails are short-circuited by message_route() before
        # _message_route_process() is ever called, so they must be logged
        # here instead: this is the only hook still reached in that case.
        server = self._mmg_get_marketing_server()
        if server:
            self.env['marketing.inbound.mail']._mmg_log_routed_message(email_message, message_dict, server)
        return super()._routing_handle_bounce(email_message, message_dict)
