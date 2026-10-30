# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .shiprocket_request import ShiprocketRequest


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('shiprocket', 'Shiprocket')],
        ondelete={'shiprocket': 'set default'},
    )

    shiprocket_email = fields.Char(string='Shiprocket Email', groups='base.group_system')
    shiprocket_password = fields.Char(string='Shiprocket Password', groups='base.group_system')
    shiprocket_token = fields.Char(string='Shiprocket Auth Token', groups='base.group_system', copy=False)

    shiprocket_pickup_location = fields.Char(
        string='Pickup Location Nickname',
        help="Must match a pickup location nickname configured in your Shiprocket account.")
    shiprocket_default_package_length = fields.Float(string='Default Package Length (cm)', default=10.0)
    shiprocket_default_package_width = fields.Float(string='Default Package Width (cm)', default=10.0)
    shiprocket_default_package_height = fields.Float(string='Default Package Height (cm)', default=10.0)
    shiprocket_default_weight = fields.Float(string='Default Weight (kg)', default=0.5)
    shiprocket_courier_id = fields.Char(
        string='Preferred Courier ID',
        help="Leave empty to let Shiprocket auto-assign the recommended courier.")

    # ------------------------------------------------------------------
    # Test connection
    # ------------------------------------------------------------------
    def action_shiprocket_test_connection(self):
        self.ensure_one()
        # Force a fresh login instead of reusing a cached token, so this genuinely
        # re-validates the email/password rather than just checking token presence.
        self.shiprocket_token = False
        client = self._shiprocket_get_client()

        pickup_warning = ''
        if self.shiprocket_pickup_location:
            try:
                locations = client._call('GET', '/settings/company/pickup')
                nicknames = [
                    loc.get('pickup_location')
                    for loc in (locations.get('data') or {}).get('shipping_address') or []
                ]
                if self.shiprocket_pickup_location not in nicknames:
                    pickup_warning = _(
                        " Warning: pickup location '%(name)s' was not found in your Shiprocket "
                        "account's pickup addresses (found: %(found)s).",
                        name=self.shiprocket_pickup_location,
                        found=', '.join(nicknames) or _('none'),
                    )
            except Exception:
                pickup_warning = _(" Could not verify the pickup location against your account.")
        else:
            pickup_warning = _(" No Pickup Location Nickname is set yet — bookings will fail until you add one.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Shiprocket connection OK"),
                'message': _("Successfully authenticated as %(email)s.", email=self.shiprocket_email) + pickup_warning,
                'type': 'warning' if pickup_warning else 'success',
                'sticky': bool(pickup_warning),
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _shiprocket_get_client(self):
        self.ensure_one()
        if not self.shiprocket_email or not self.shiprocket_password:
            raise UserError(_("Please configure your Shiprocket credentials on the delivery method."))
        client = ShiprocketRequest(self.shiprocket_email, self.shiprocket_password, self.shiprocket_token)
        if not self.shiprocket_token:
            token = client.authenticate()
            self.sudo().shiprocket_token = token
        return client

    def _shiprocket_get_weight(self, order=None, picking=None):
        self.ensure_one()
        weight = 0.0
        if picking:
            weight = sum(picking.move_ids.mapped('product_qty') and picking.move_ids.mapped(
                lambda m: m.product_qty * (m.product_id.weight or 0.0)) or [0.0])
        elif order:
            weight = sum(order.order_line.filtered(lambda l: not l.is_delivery).mapped(
                lambda l: l.product_uom_qty * (l.product_id.weight or 0.0)))
        return weight or self.shiprocket_default_weight

    def _shiprocket_build_order_vals(self, picking):
        self.ensure_one()
        sale_order = picking.sale_id
        partner = picking.partner_id
        warehouse_partner = picking.picking_type_id.warehouse_id.partner_id

        if not (partner.phone or partner.mobile):
            raise UserError(_(
                "%(partner)s has no phone number set. Shiprocket requires a billing phone "
                "number to create the shipment.", partner=partner.name))

        name_parts = (partner.name or '').strip().split(' ', 1)
        billing_first_name = name_parts[0] if name_parts else ''
        billing_last_name = name_parts[1] if len(name_parts) > 1 else billing_first_name

        order_items = []
        for move in picking.move_ids:
            order_items.append({
                'name': move.product_id.name,
                'sku': move.product_id.default_code or str(move.product_id.id),
                'units': int(move.quantity or move.product_qty),
                'selling_price': move.sale_line_id.price_unit if move.sale_line_id else move.product_id.list_price,
            })

        return {
            'order_id': picking.name,
            'order_date': fields.Date.to_string(picking.scheduled_date or fields.Date.today()),
            'pickup_location': self.shiprocket_pickup_location,
            'billing_customer_name': billing_first_name,
            'billing_last_name': billing_last_name,
            'billing_address': partner.street or '',
            'billing_address_2': partner.street2 or '',
            'billing_city': partner.city or '',
            'billing_pincode': partner.zip or '',
            'billing_state': partner.state_id.name or '',
            'billing_country': partner.country_id.name or 'India',
            'billing_email': partner.email or '',
            'billing_phone': partner.phone or partner.mobile or '',
            'shipping_is_billing': True,
            'order_items': order_items,
            'payment_method': 'COD' if sale_order and sale_order.payment_term_id and 'cod' in (sale_order.payment_term_id.name or '').lower() else 'Prepaid',
            'sub_total': sum(item['selling_price'] * item['units'] for item in order_items),
            'length': self.shiprocket_default_package_length,
            'breadth': self.shiprocket_default_package_width,
            'height': self.shiprocket_default_package_height,
            'weight': self._shiprocket_get_weight(picking=picking),
        }

    # ------------------------------------------------------------------
    # Provider API (see addons/delivery/models/delivery_carrier.py)
    # ------------------------------------------------------------------
    def shiprocket_rate_shipment(self, order):
        self.ensure_one()
        client = self._shiprocket_get_client()
        warehouse_partner = order.warehouse_id.partner_id
        delivery_partner = order.partner_shipping_id

        if not warehouse_partner.zip or not delivery_partner.zip:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _("Missing pickup or delivery pincode."),
                'warning_message': False,
            }

        weight = self._shiprocket_get_weight(order=order)
        is_cod = bool(order.payment_term_id and 'cod' in (order.payment_term_id.name or '').lower())

        result = client.check_serviceability(
            warehouse_partner.zip, delivery_partner.zip, weight, is_cod,
            declared_value=order.amount_total,
        )
        companies = (result.get('data') or {}).get('available_courier_companies') or []
        if not companies:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _("No courier is serviceable for this route."),
                'warning_message': False,
            }

        cheapest = min(companies, key=lambda c: c.get('rate', float('inf')))
        return {
            'success': True,
            'price': cheapest.get('rate', 0.0),
            'error_message': False,
            'warning_message': False,
        }

    def shiprocket_send_shipping(self, pickings):
        res = []
        for picking in pickings:
            client = self._shiprocket_get_client()
            order_vals = self._shiprocket_build_order_vals(picking)
            order_resp = client.create_order(order_vals)

            shipment_id = order_resp.get('shipment_id')
            if not shipment_id:
                raise UserError(_("Shiprocket did not return a shipment for %s: %s", picking.name, order_resp))

            awb_resp = client.assign_awb(shipment_id, self.shiprocket_courier_id or None)
            awb_data = (awb_resp.get('response') or {}).get('data') or {}
            tracking_number = awb_data.get('awb_code') or ''
            charge = awb_data.get('courier_charge') or awb_data.get('freight_charges') or 0.0

            client.request_pickup([shipment_id])

            picking.shiprocket_shipment_id = shipment_id
            picking.shiprocket_order_id = order_resp.get('order_id')
            picking.shiprocket_status = 'awb_assigned' if tracking_number else 'pickup_generated'

            res.append({
                'exact_price': charge,
                'tracking_number': tracking_number,
            })

        # Generate label/manifest once carrier_tracking_ref is set on the pickings by the caller.
        pickings.action_shiprocket_generate_label()
        pickings.action_shiprocket_generate_manifest()
        return res

    def shiprocket_get_tracking_link(self, picking):
        self.ensure_one()
        if not picking.carrier_tracking_ref:
            return False
        return f'https://shiprocket.co/tracking/{picking.carrier_tracking_ref}'

    def shiprocket_cancel_shipment(self, pickings):
        for picking in pickings:
            client = self._shiprocket_get_client()
            if picking.carrier_tracking_ref:
                client.cancel_shipment([picking.carrier_tracking_ref])
            elif picking.shiprocket_order_id:
                client.cancel_order([picking.shiprocket_order_id])
            picking.message_post(body=_("Shipment cancelled on Shiprocket."))
        pickings.write({'carrier_tracking_ref': False})
