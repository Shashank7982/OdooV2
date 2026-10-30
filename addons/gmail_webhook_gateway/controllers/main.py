# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GmailWebhookController(http.Controller):

    @http.route('/gmail_webhook_gateway/oauth/callback', type='http', auth='user', csrf=False)
    def oauth_callback(self, code=None, state=None, error=None, **kwargs):
        """Google redirects here after the user grants/denies consent."""
        if error:
            return request.render('gmail_webhook_gateway.oauth_error', {'error': error})
        account = request.env['gmail.webhook.account'].browse(int(state)) if state else None
        if not account or not account.exists():
            return request.render('gmail_webhook_gateway.oauth_error', {'error': 'Unknown account'})
        try:
            account._oauth_exchange_code(code)
        except Exception as exc:  # noqa: BLE001
            _logger.exception('Gmail OAuth callback failed for account %s', account.id)
            return request.render('gmail_webhook_gateway.oauth_error', {'error': str(exc)})
        return request.redirect('/odoo')

    @http.route('/gmail_webhook_gateway/webhook/<string:token>', type='json', auth='public', csrf=False,
                methods=['POST'])
    def gmail_webhook(self, token, **kwargs):
        """Google Cloud Pub/Sub push endpoint. Google POSTs a JSON envelope
        here every time the watched mailbox changes. Returning a non-2xx
        status makes Pub/Sub retry the push, so genuine processing failures
        are allowed to raise (logged by the framework) rather than being
        swallowed - a missed push is worse than a retried one."""
        account = request.env['gmail.webhook.account'].sudo().search([('webhook_token', '=', token)], limit=1)
        if not account:
            _logger.warning('Gmail webhook called with an unknown token')
            return request.make_json_response({'error': 'unknown token'}, status=404)

        envelope = request.get_json_data()
        account._process_pubsub_push(envelope)
        return request.make_json_response({'status': 'ok'})
