from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class AffiliatePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        affiliate = request.env['sale.affiliate'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1,
        )
        if 'affiliate_count' in counters:
            values['affiliate_count'] = 1 if affiliate else 0
        return values

    @http.route(['/my/affiliate'], type='http', auth='user', website=True)
    def portal_my_affiliate(self, **kw):
        partner = request.env.user.partner_id
        affiliate = request.env['sale.affiliate'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1,
        )
        if not affiliate:
            return request.redirect('/my')

        commissions = request.env['affiliate.commission'].sudo().search(
            [('affiliate_id', '=', affiliate.id)], order='create_date desc',
        )
        withdrawals = request.env['affiliate.withdrawal'].sudo().search(
            [('affiliate_id', '=', affiliate.id)], order='create_date desc',
        )
        clicks = request.env['affiliate.click'].sudo().search(
            [('affiliate_id', '=', affiliate.id)], order='click_date desc', limit=50,
        )

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        affiliate_link = '%s/affiliate/%s' % (base_url, affiliate.key)

        values = self._prepare_portal_layout_values()
        values.update({
            'affiliate': affiliate,
            'commissions': commissions,
            'withdrawals': withdrawals,
            'clicks': clicks,
            'affiliate_link': affiliate_link,
            'page_name': 'affiliate',
        })
        return request.render(
            'website_sale_affiliate_custom.portal_my_affiliate', values,
        )

    @http.route(['/my/affiliate/withdraw'], type='http', auth='user', website=True, methods=['POST'])
    def portal_affiliate_withdraw(self, **post):
        partner = request.env.user.partner_id
        affiliate = request.env['sale.affiliate'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1,
        )
        if not affiliate:
            return request.redirect('/my')

        amount = float(post.get('amount', 0))
        min_amount = float(
            request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_affiliate_custom.min_withdrawal_amount', '50.0',
            )
        )

        if amount >= min_amount and amount <= affiliate.pending_commission:
            withdrawal = request.env['affiliate.withdrawal'].sudo().create({
                'affiliate_id': affiliate.id,
                'amount': amount,
            })
            # Auto-approve if configured
            auto_approve = request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_affiliate_custom.auto_approve_withdrawals', 'False',
            )
            if auto_approve == 'True':
                withdrawal.action_approve()

        return request.redirect('/my/affiliate')
