# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .ithink_request import IThinkRequest


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('ithink', 'iThink Logistics')],
        ondelete={'ithink': 'set default'},
    )

    ithink_access_token = fields.Char(string='Access Token', groups='base.group_system')
    ithink_secret_key = fields.Char(string='Secret Key', groups='base.group_system')
    ithink_test_mode = fields.Boolean(string='Use Staging Environment', default=False)

    ithink_pickup_address_id = fields.Char(
        string='Pickup Address ID',
        help="Warehouse/pickup address ID configured in your iThink Logistics account.")
    ithink_return_address_id = fields.Char(
        string='Return Address ID',
        help="Optional. Return address ID configured in your iThink Logistics account.")
    ithink_logistics = fields.Char(
        string='Preferred Logistics Partner',
        help="Leave empty to let iThink Logistics auto-assign the recommended courier "
             "(e.g. delhivery, bluedart, xpressbees, ecom, ekart).")

    ithink_default_package_length = fields.Float(string='Default Package Length (cm)', default=10.0)
    ithink_default_package_width = fields.Float(string='Default Package Width (cm)', default=10.0)
    ithink_default_package_height = fields.Float(string='Default Package Height (cm)', default=10.0)
    ithink_default_weight = fields.Float(string='Default Weight (kg)', default=0.5)

    # ------------------------------------------------------------------
    # Test connection
    # ------------------------------------------------------------------
    def action_ithink_test_connection(self):
        self.ensure_one()
        client = self._ithink_get_client()

        warning = ''
        if not self.ithink_pickup_address_id:
            warning = _(" No Pickup Address ID is set yet — bookings will fail until you add one.")
        else:
            try:
                client.check_pincode('400001')
            except UserError as e:
                raise UserError(_("Connection failed: %s", e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("iThink Logistics connection OK"),
                'message': _("Successfully authenticated with iThink Logistics.") + warning,
                'type': 'warning' if warning else 'success',
                'sticky': bool(warning),
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ithink_get_client(self):
        self.ensure_one()
        if not self.ithink_access_token or not self.ithink_secret_key:
            raise UserError(_("Please configure your iThink Logistics credentials on the delivery method."))
        return IThinkRequest(self.ithink_access_token, self.ithink_secret_key, test_mode=self.ithink_test_mode)

    def _ithink_get_weight(self, order=None, picking=None):
        self.ensure_one()
        weight = 0.0
        if picking:
            weight = sum(picking.move_ids.mapped(
                lambda m: m.product_qty * (m.product_id.weight or 0.0)))
        elif order:
            weight = sum(order.order_line.filtered(lambda l: not l.is_delivery).mapped(
                lambda l: l.product_uom_qty * (l.product_id.weight or 0.0)))
        return weight or self.ithink_default_weight

    @staticmethod
    def _ithink_normalize_phone(number, partner_name):
        """ iThink Logistics requires a bare 10-digit Indian mobile number:
        no country code, spaces or punctuation. """
        digits = ''.join(ch for ch in (number or '') if ch.isdigit())
        if len(digits) > 10 and digits.startswith('91'):
            digits = digits[2:]
        if len(digits) > 10:
            digits = digits[-10:]
        if len(digits) != 10:
            raise UserError(_(
                "%(partner)s's phone number (%(number)s) is not a valid 10-digit mobile "
                "number. iThink Logistics requires a plain 10-digit number without country "
                "code.", partner=partner_name, number=number))
        return digits

    def _ithink_build_shipment_vals(self, picking):
        self.ensure_one()
        sale_order = picking.sale_id
        partner = picking.partner_id

        if not (partner.phone or partner.mobile):
            raise UserError(_(
                "%(partner)s has no phone number set. iThink Logistics requires a phone "
                "number to create the shipment.", partner=partner.name))

        main_phone = self._ithink_normalize_phone(partner.phone or partner.mobile, partner.name)
        alt_phone = ''
        if partner.mobile and partner.phone and partner.mobile != partner.phone:
            try:
                alt_phone = self._ithink_normalize_phone(partner.mobile, partner.name)
            except UserError:
                alt_phone = ''

        products = []
        for move in picking.move_ids:
            products.append({
                'product_name': move.product_id.name,
                'product_sku': move.product_id.default_code or str(move.product_id.id),
                'product_quantity': str(int(move.quantity or move.product_qty)),
                'product_price': str(move.sale_line_id.price_unit if move.sale_line_id else move.product_id.list_price),
                'product_tax_rate': '0',
                'product_hsn_code': move.product_id.l10n_in_hsn_code if 'l10n_in_hsn_code' in move.product_id._fields else '',
                'product_discount': '0',
            })

        is_cod = bool(sale_order and sale_order.payment_term_id and 'cod' in (sale_order.payment_term_id.name or '').lower())
        total_amount = sum(float(p['product_price']) * int(p['product_quantity']) for p in products)

        vals = {
            'waybill': '',
            'order': picking.name,
            'sub_order': sale_order.name if sale_order else picking.name,
            'order_date': fields.Date.to_string(picking.scheduled_date or fields.Date.today()),
            'total_amount': str(total_amount),
            'name': partner.name or '',
            'company_name': partner.commercial_company_name or '',
            'add': partner.street or '',
            'add2': partner.street2 or '',
            'add3': '',
            'pin': partner.zip or '',
            'city': partner.city or '',
            'state': partner.state_id.name or '',
            'country': partner.country_id.name or 'India',
            'phone': main_phone,
            'alt_phone': alt_phone,
            'email': partner.email or '',
            'is_billing_same_as_shipping': 'yes',
            'products': products,
            'shipment_length': str(self.ithink_default_package_length),
            'shipment_width': str(self.ithink_default_package_width),
            'shipment_height': str(self.ithink_default_package_height),
            'weight': str(self._ithink_get_weight(picking=picking) * 1000),  # kg -> g
            'shipping_charges': '0',
            'giftwrap_charges': '0',
            'transaction_charges': '0',
            'total_discount': '0',
            'first_attemp_discount': '0',
            'cod_charges': '0',
            'advance_amount': '0',
            'cod_amount': str(total_amount) if is_cod else '0',
            'payment_mode': 'COD' if is_cod else 'Prepaid',
            'reseller_name': '',
            'eway_bill_number': '',
            'gst_number': '',
            'what3words': '',
        }
        if self.ithink_return_address_id:
            vals['return_address_id'] = self.ithink_return_address_id
        return vals

    # ------------------------------------------------------------------
    # Provider API (see addons/delivery/models/delivery_carrier.py)
    # ------------------------------------------------------------------
    def ithink_rate_shipment(self, order):
        self.ensure_one()
        client = self._ithink_get_client()
        warehouse_partner = order.warehouse_id.partner_id
        delivery_partner = order.partner_shipping_id

        if not warehouse_partner.zip or not delivery_partner.zip:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _("Missing pickup or delivery pincode."),
                'warning_message': False,
            }

        weight = self._ithink_get_weight(order=order)
        is_cod = bool(order.payment_term_id and 'cod' in (order.payment_term_id.name or '').lower())

        result = client.get_rate(
            warehouse_partner.zip, delivery_partner.zip, weight,
            self.ithink_default_package_length, self.ithink_default_package_width, self.ithink_default_package_height,
            payment_method='cod' if is_cod else 'prepaid',
            product_mrp=order.amount_total,
        )
        rates = result.get('data') or []
        if not rates:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _("No courier is serviceable for this route."),
                'warning_message': False,
            }

        if self.ithink_logistics:
            matching = [r for r in rates if (r.get('logistic_name') or '').lower() == self.ithink_logistics.lower()]
            rates = matching or rates

        cheapest = min(rates, key=lambda r: r.get('rate', float('inf')))
        return {
            'success': True,
            'price': cheapest.get('rate', 0.0),
            'error_message': False,
            'warning_message': False,
        }

    def ithink_send_shipping(self, pickings):
        res = []
        for picking in pickings:
            client = self._ithink_get_client()
            if not self.ithink_pickup_address_id:
                raise UserError(_("Please configure a Pickup Address ID on the delivery method."))

            shipment_vals = self._ithink_build_shipment_vals(picking)
            order_resp = client.add_order(shipment_vals, self.ithink_pickup_address_id, logistics=self.ithink_logistics or '')

            result_data = (order_resp.get('data') or {}).get('1') or {}
            if (result_data.get('status') or '').lower() != 'success':
                raise UserError(_("iThink Logistics did not confirm the order for %(picking)s: %(remark)s",
                                   picking=picking.name, remark=result_data.get('remark') or order_resp))

            tracking_number = result_data.get('waybill') or ''
            picking.ithink_awb_number = tracking_number
            picking.ithink_logistic_name = result_data.get('logistic_name') or ''
            picking.ithink_tracking_url = result_data.get('tracking_url') or ''
            picking.ithink_status = 'booked'

            res.append({
                'exact_price': 0.0,
                'tracking_number': tracking_number,
            })

        pickings.action_ithink_generate_label()
        pickings.action_ithink_generate_manifest()
        return res

    def ithink_get_tracking_link(self, picking):
        self.ensure_one()
        return picking.ithink_tracking_url or False

    def ithink_cancel_shipment(self, pickings):
        for picking in pickings:
            client = self._ithink_get_client()
            if picking.carrier_tracking_ref:
                client.cancel_order([picking.carrier_tracking_ref])
                picking.ithink_status = 'cancelled'
            picking.message_post(body=_("Shipment cancelled on iThink Logistics."))
        pickings.write({'carrier_tracking_ref': False})
