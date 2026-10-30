from odoo import http
from odoo.http import request


class WebsiteSaleAffiliate(http.Controller):

    @http.route(['/affiliate/<string:key>'], type='http', auth='public', website=True)
    def affiliate_redirect(self, key, redirect='/', **kwargs):
        """Redirect from an affiliate link, storing affiliate in session."""
        affiliate = request.env['sale.affiliate'].sudo().search([('key', '=', key)], limit=1)
        if affiliate:
            request.session['sale_affiliate_id'] = affiliate.id
        return request.redirect(redirect)
