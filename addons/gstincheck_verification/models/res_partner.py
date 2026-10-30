import json

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

BASE_URL = 'https://sheet.gstincheck.co.in/check'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gst_verification_status = fields.Selection(
        [('not_verified', 'Not Verified'), ('verified', 'Verified'),
         ('invalid', 'Invalid'), ('error', 'Error')],
        string='GSTIN Verification', default='not_verified', readonly=True, copy=False,
    )
    gst_verified_at = fields.Datetime(string='Verified At', readonly=True, copy=False)
    gst_verified_legal_name = fields.Char(string='GST Legal Name', readonly=True, copy=False)
    gst_verified_trade_name = fields.Char(string='GST Trade Name', readonly=True, copy=False)
    gst_verified_pan = fields.Char(string='GST PAN (from GSTIN)', readonly=True, copy=False)
    gst_verified_registration_status = fields.Char(string='GST Registration Status', readonly=True, copy=False)
    gst_verified_registration_date = fields.Char(string='GST Registration Date', readonly=True, copy=False)
    gst_verified_state = fields.Char(string='GST State', readonly=True, copy=False)
    gst_verified_address = fields.Char(string='GST Registered Address', readonly=True, copy=False)
    gst_verification_message = fields.Text(string='GST Verification Message', readonly=True, copy=False)
    gst_verification_response = fields.Text(string='GST API Response', readonly=True, copy=False)

    @api.onchange('vat')
    def _onchange_vat_reset_gst_verification(self):
        for partner in self:
            if partner._origin.vat and partner.vat != partner._origin.vat:
                partner.gst_verification_status = 'not_verified'

    def action_verify_gstin(self):
        for partner in self:
            partner.ensure_one()
            gstin = (partner.vat or '').strip().upper()
            if not gstin:
                raise UserError(_('Enter a GSTIN before verification.'))

            company = partner.company_id or self.env.company
            if not company.gst_check_enabled:
                raise UserError(_('Enable GSTIN Verification on the company first.'))
            if not company.gst_check_api_key:
                raise UserError(_('Enter the gstincheck.co.in API key on the company first.'))

            try:
                response = requests.get(
                    f'{BASE_URL}/{company.gst_check_api_key}/{gstin}',
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as error:
                partner.sudo().write({
                    'gst_verification_status': 'error',
                    'gst_verified_at': fields.Datetime.now(),
                    'gst_verification_message': str(error),
                    'gst_verification_response': False,
                })
                raise UserError(_('GSTIN verification failed: %s', error)) from error

            found = payload.get('flag') is True
            data = payload.get('data') or {}

            if not found:
                partner.sudo().write({
                    'gst_verification_status': 'invalid',
                    'gst_verified_at': fields.Datetime.now(),
                    'gst_verified_legal_name': False,
                    'gst_verified_trade_name': False,
                    'gst_verified_pan': False,
                    'gst_verified_registration_status': False,
                    'gst_verified_registration_date': False,
                    'gst_verified_state': False,
                    'gst_verified_address': False,
                    'gst_verification_message': payload.get('message') or _('GSTIN not found.'),
                    'gst_verification_response': json.dumps(payload, indent=2, sort_keys=True),
                })
                continue

            status = (data.get('sts') or '').strip()
            verified_status = 'verified' if status.lower() == 'active' else 'invalid'
            message = _('GSTIN is valid and active.') if verified_status == 'verified' else _(
                'GSTIN was found but is not active (status: %s).', status or _('unknown')
            )
            principal_address = (data.get('pradr') or {}).get('adr')
            principal_state = ((data.get('pradr') or {}).get('addr') or {}).get('stcd')
            # PAN is embedded in a GSTIN: characters 3-12 (0-indexed [2:12]).
            pan = gstin[2:12] if len(gstin) >= 12 else False

            partner.sudo().write({
                'gst_verification_status': verified_status,
                'gst_verified_at': fields.Datetime.now(),
                'gst_verified_legal_name': data.get('lgnm') or False,
                'gst_verified_trade_name': data.get('tradeNam') or False,
                'gst_verified_pan': pan,
                'gst_verified_registration_status': status or False,
                'gst_verified_registration_date': data.get('rgdt') or False,
                'gst_verified_state': principal_state or False,
                'gst_verified_address': principal_address or False,
                'gst_verification_message': message,
                'gst_verification_response': json.dumps(payload, indent=2, sort_keys=True),
            })
        return {'type': 'ir.actions.client', 'tag': 'reload'}
