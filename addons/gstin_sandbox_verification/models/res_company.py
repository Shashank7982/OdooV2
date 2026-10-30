from datetime import timedelta

import requests

from odoo import fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    gst_sandbox_enabled = fields.Boolean(string='Enable GSTIN Verification', default=False)
    gst_sandbox_environment = fields.Selection(
        [('test', 'Test'), ('production', 'Production')],
        string='Sandbox Environment', default='test', required=True,
    )
    gst_sandbox_api_key = fields.Char(string='Sandbox API Key', copy=False)
    gst_sandbox_api_secret = fields.Char(string='Sandbox API Secret', copy=False)
    gst_sandbox_access_token = fields.Char(string='Sandbox Access Token', copy=False)
    gst_sandbox_token_expires_at = fields.Datetime(string='Sandbox Token Expiry', copy=False)
    gst_sandbox_token_environment = fields.Selection(
        [('test', 'Test'), ('production', 'Production')],
        string='Sandbox Token Environment', copy=False,
        help="Environment the cached access token was issued for. Used to invalidate "
             "the cache when switching between Test and Production.",
    )

    def _gst_sandbox_base_url(self):
        self.ensure_one()
        return (
            'https://test-api.sandbox.co.in'
            if self.gst_sandbox_environment == 'test'
            else 'https://api.sandbox.co.in'
        )

    def _gst_sandbox_get_access_token(self):
        self.ensure_one()
        if not self.gst_sandbox_enabled:
            raise UserError(_('Enable GSTIN Verification on the company first.'))
        if not self.gst_sandbox_api_key or not self.gst_sandbox_api_secret:
            raise UserError(_('Enter the Sandbox API key and API secret first.'))

        now = fields.Datetime.now()
        if (
            self.gst_sandbox_access_token
            and self.gst_sandbox_token_expires_at
            and self.gst_sandbox_token_environment == self.gst_sandbox_environment
        ):
            if self.gst_sandbox_token_expires_at > now + timedelta(minutes=2):
                return self.gst_sandbox_access_token

        try:
            response = requests.post(
                f'{self._gst_sandbox_base_url()}/authenticate',
                headers={
                    'x-api-key': self.gst_sandbox_api_key,
                    'x-api-secret': self.gst_sandbox_api_secret,
                    'x-api-version': '1.0.0',
                    'Content-Type': 'application/json',
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise UserError(_('Sandbox authentication failed: %s', error)) from error

        token = (payload.get('data') or {}).get('access_token')
        if not token:
            raise UserError(_('Sandbox authentication returned no access token.'))

        self.sudo().write({
            'gst_sandbox_access_token': token,
            'gst_sandbox_token_expires_at': now + timedelta(hours=24),
            'gst_sandbox_token_environment': self.gst_sandbox_environment,
        })
        return token
