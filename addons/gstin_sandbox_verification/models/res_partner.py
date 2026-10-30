import json

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
    gst_verified_pan = fields.Char(string='GST PAN from API', readonly=True, copy=False)
    gst_verified_registration_status = fields.Char(string='GST Registration Status', readonly=True, copy=False)
    gst_verified_registration_date = fields.Char(string='GST Registration Date', readonly=True, copy=False)
    gst_verified_state = fields.Char(string='GST State', readonly=True, copy=False)
    gst_verified_transaction_id = fields.Char(string='GST API Transaction ID', readonly=True, copy=False)
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
            token = company._gst_sandbox_get_access_token()
            try:
                response = requests.post(
                    f'{company._gst_sandbox_base_url()}/gst/compliance/public/gstin/verify',
                    headers={
                        'x-api-key': company.gst_sandbox_api_key,
                        'authorization': token,
                        'x-api-version': '1.0.0',
                        'Content-Type': 'application/json',
                    },
                    json={'gstin': gstin},
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

            result = ((payload.get('data') or {}).get('data') or {})
            valid = result.get('validGstin') is True
            status = (result.get('status') or '').strip()
            verified_status = 'verified' if valid and status.lower() == 'active' else 'invalid'
            message = _('GSTIN is valid and active.') if verified_status == 'verified' else _(
                'GSTIN was returned by the API but is not valid and active.'
            )
            partner.sudo().write({
                'gst_verification_status': verified_status,
                'gst_verified_at': fields.Datetime.now(),
                'gst_verified_legal_name': result.get('legalName') or False,
                'gst_verified_trade_name': result.get('tradeName') or False,
                'gst_verified_pan': result.get('pan') or False,
                'gst_verified_registration_status': status or False,
                'gst_verified_registration_date': result.get('regStartDate') or False,
                'gst_verified_state': result.get('stateName') or False,
                'gst_verified_transaction_id': payload.get('transaction_id') or False,
                'gst_verification_message': message,
                'gst_verification_response': json.dumps(payload, indent=2, sort_keys=True),
            })
        return {'type': 'ir.actions.client', 'tag': 'reload'}
