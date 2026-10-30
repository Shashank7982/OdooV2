from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _preprocess_request(cls):
        super()._preprocess_request()
        if not request or not request.httprequest:
            return

        # Check for affiliate query parameters: 'aff_ref' or 'ref'
        aff_ref = request.httprequest.args.get('aff_ref') or request.httprequest.args.get('ref')
        if aff_ref:
            # Search for the affiliate
            affiliate = request.env['sale.affiliate'].sudo().search([
                '|', ('key', '=', aff_ref), ('id', '=', int(aff_ref) if aff_ref.isdigit() else 0)
            ], limit=1)
            if affiliate:
                # Store in session
                request.session['sale_affiliate_id'] = affiliate.id
                # Record click in request context (custom extension will handle saving it to DB)
                request.env.context = dict(request.env.context, affiliate_ref_detected=affiliate.id)
