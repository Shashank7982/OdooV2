# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request

from odoo.addons.sale.controllers.portal import CustomerPortal


class SaleSnailmailPortal(CustomerPortal):

    @http.route('/my/orders/<int:order_id>/send_by_post', type='http', methods=['POST'], auth='public', website=True)
    def portal_order_send_by_post(self, order_id, access_token=None, **kwargs):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        params = {'access_token': access_token} if access_token else {}
        try:
            order_sudo._snailmail_create_letter(user=request.env.user)
            params['snailmail_sent'] = 1
        except UserError as e:
            params['snailmail_error'] = str(e)

        return request.redirect(order_sudo.get_portal_url(query_string='&' + http.url_encode(params)))
