from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteFormMetaPixel(WebsiteForm):

    def insert_record(self, request, model, values, custom, meta=None):
        record_id = super().insert_record(request, model, values, custom, meta=meta)
        if model.sudo().model == 'crm.lead' and record_id:
            request.env['meta.pixel.event'].sudo().create({
                'event_type': 'lead',
                'website_id': request.website.id if request.website else False,
                'url': request.httprequest.path,
                'lead_id': record_id,
            })
        return record_id


class WebsiteSaleMetaPixel(WebsiteSale):

    def _prepare_shop_payment_confirmation_values(self, order):
        values = super()._prepare_shop_payment_confirmation_values(order)
        already_logged = request.env['meta.pixel.event'].sudo().search_count([
            ('event_type', '=', 'purchase'),
            ('sale_order_id', '=', order.id),
        ])
        if not already_logged:
            request.env['meta.pixel.event'].sudo().create({
                'event_type': 'purchase',
                'website_id': order.website_id.id if order.website_id else False,
                'url': '/shop/confirmation',
                'value': order.amount_total,
                'currency_id': order.currency_id.id,
                'partner_id': order.partner_id.id,
                'sale_order_id': order.id,
            })
        return values


class MetaPixelTracking(http.Controller):

    @http.route('/meta_pixel/track_pageview', type='json', auth='public', website=True, csrf=False)
    def track_pageview(self, url=None, **kwargs):
        request.env['meta.pixel.event'].sudo().create({
            'event_type': 'page_view',
            'website_id': request.website.id if request.website else False,
            'url': url or request.httprequest.referrer,
        })
        return {}
