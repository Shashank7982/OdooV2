from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Shipping / Shiprocket
    # ------------------------------------------------------------------
    gst_shiprocket_order_id = fields.Char(compute='_compute_gst_shipping_info', store=True, string='Shiprocket Order ID')
    gst_shiprocket_awb = fields.Char(compute='_compute_gst_shipping_info', store=True, string='AWB / Tracking Number')
    gst_shiprocket_courier = fields.Char(compute='_compute_gst_shipping_info', store=True, string='Courier / Transport Partner')
    gst_shiprocket_status = fields.Char(compute='_compute_gst_shipping_info', store=True, string='Shipment Status')
    gst_shiprocket_tracking_url = fields.Char(compute='_compute_gst_shipping_info', store=True, string='Tracking URL')

    gst_shipping_contact_name = fields.Char(compute='_compute_gst_shipping_info', store=True, string='Shipping Contact')
    gst_shipping_contact_number = fields.Char(compute='_compute_gst_shipping_info', store=True, string='Shipping Contact Number')

    @api.depends('invoice_line_ids.sale_line_ids.order_id.picking_ids', 'partner_shipping_id')
    def _compute_gst_shipping_info(self):
        for move in self:
            picking = False
            orders = move.invoice_line_ids.sale_line_ids.order_id
            if orders:
                pickings = orders.picking_ids.filtered(lambda p: p.carrier_tracking_ref or getattr(p, 'shiprocket_shipment_id', False))
                picking = pickings[:1]

            if picking and hasattr(picking, 'shiprocket_shipment_id'):
                move.gst_shiprocket_order_id = picking.shiprocket_order_id
                move.gst_shiprocket_awb = picking.carrier_tracking_ref
                move.gst_shiprocket_courier = picking.carrier_id.name if picking.carrier_id else False
                move.gst_shiprocket_status = dict(
                    picking._fields['shiprocket_status'].selection
                ).get(picking.shiprocket_status) if picking.shiprocket_status else False
                move.gst_shiprocket_tracking_url = (
                    picking.carrier_id.shiprocket_get_tracking_link(picking)
                    if picking.carrier_id and picking.carrier_tracking_ref and hasattr(picking.carrier_id, 'shiprocket_get_tracking_link')
                    else False
                )
            else:
                move.gst_shiprocket_order_id = False
                move.gst_shiprocket_awb = False
                move.gst_shiprocket_courier = False
                move.gst_shiprocket_status = False
                move.gst_shiprocket_tracking_url = False

            shipping_partner = move.partner_shipping_id or move.partner_id
            move.gst_shipping_contact_name = shipping_partner.gst_contact_person or shipping_partner.name
            move.gst_shipping_contact_number = shipping_partner.gst_contact_number or shipping_partner.phone or shipping_partner.mobile

    # ------------------------------------------------------------------
    # Coupon / manual / affiliate discount (customer-safe fields only)
    # ------------------------------------------------------------------
    gst_coupon_code = fields.Char(compute='_compute_gst_discount_info', store=True, string='Coupon Code')
    gst_coupon_discount_amount = fields.Monetary(compute='_compute_gst_discount_info', store=True, string='Coupon Discount')
    gst_manual_discount_amount = fields.Monetary(compute='_compute_gst_discount_info', store=True, string='Manual Discount')
    gst_affiliate_code = fields.Char(compute='_compute_gst_discount_info', store=True, string='Affiliate/Referral Code')
    gst_affiliate_discount_amount = fields.Monetary(compute='_compute_gst_discount_info', store=True, string='Affiliate Discount')
    # Not computed on purpose: lets this be wired up manually to a future campaign feature
    # without depending on any specific affiliate/marketing module being installed.
    gst_campaign_name = fields.Char(string='Campaign Name')

    @api.depends(
        'invoice_line_ids.discount', 'invoice_line_ids.price_unit', 'invoice_line_ids.quantity',
        'invoice_line_ids.sale_line_ids.order_id.affiliate_id',
        'invoice_line_ids.sale_line_ids.order_id.applied_coupon_ids',
    )
    def _compute_gst_discount_info(self):
        for move in self:
            orders = move.invoice_line_ids.sale_line_ids.order_id
            order = orders[:1]

            total_discount = sum(
                line.price_unit * line.quantity * (line.discount or 0.0) / 100.0
                for line in move.invoice_line_ids
                if line.display_type == 'product'
            )

            coupon_code = False
            coupon_discount = 0.0
            if order and hasattr(order, 'applied_coupon_ids') and order.applied_coupon_ids:
                coupon_code = ', '.join(order.applied_coupon_ids.mapped('code'))
                reward_lines = order.order_line.filtered(lambda l: getattr(l, 'reward_id', False))
                coupon_discount = abs(sum(reward_lines.mapped('price_subtotal')))

            affiliate_code = False
            affiliate_discount = 0.0
            if order and getattr(order, 'affiliate_id', False):
                affiliate_code = order.affiliate_id.key or order.affiliate_id.name
                affiliate_discount = sum(
                    line.price_unit * line.quantity * (line.discount or 0.0) / 100.0
                    for line in move.invoice_line_ids
                    if line.display_type == 'product'
                )

            move.gst_coupon_code = coupon_code
            move.gst_coupon_discount_amount = coupon_discount
            move.gst_affiliate_code = affiliate_code
            move.gst_affiliate_discount_amount = affiliate_discount
            move.gst_manual_discount_amount = max(0.0, total_discount - coupon_discount - affiliate_discount)

    # ------------------------------------------------------------------
    # Shipping charges (separate GST breakup, no double counting)
    # ------------------------------------------------------------------
    gst_shipping_taxable_amount = fields.Monetary(compute='_compute_gst_shipping_charges', store=True, string='Shipping Taxable Value')
    gst_shipping_tax_amount = fields.Monetary(compute='_compute_gst_shipping_charges', store=True, string='Shipping GST Amount')
    gst_shipping_total_amount = fields.Monetary(compute='_compute_gst_shipping_charges', store=True, string='Shipping Total')

    @api.depends('invoice_line_ids.sale_line_ids.is_delivery', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.price_total')
    def _compute_gst_shipping_charges(self):
        for move in self:
            shipping_lines = move.invoice_line_ids.filtered(lambda l: l._gst_is_shipping_line())
            move.gst_shipping_taxable_amount = sum(shipping_lines.mapped('price_subtotal'))
            move.gst_shipping_total_amount = sum(shipping_lines.mapped('price_total'))
            move.gst_shipping_tax_amount = move.gst_shipping_total_amount - move.gst_shipping_taxable_amount

    def gst_get_shipping_lines(self):
        return self.invoice_line_ids.filtered(lambda l: l._gst_is_shipping_line())

    def gst_get_product_lines(self):
        return self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product' and not l._gst_is_shipping_line()
        )

    # ------------------------------------------------------------------
    # UPI QR code
    # ------------------------------------------------------------------
    gst_upi_qr_url = fields.Char(compute='_compute_gst_upi_qr_url', string='UPI QR Code URL')

    @api.depends('company_id.l10n_in_upi_id', 'company_id.gst_show_upi_qr', 'amount_total', 'name')
    def _compute_gst_upi_qr_url(self):
        for move in self:
            company = move.company_id
            if not (company.gst_show_upi_qr and company.l10n_in_upi_id):
                move.gst_upi_qr_url = False
                continue

            merchant_name = company.gst_qr_merchant_name or company.name or ''
            note = f'Invoice {move.name or ""}'.strip()
            params = f'pa={quote(company.l10n_in_upi_id)}&pn={quote(merchant_name)}&tn={quote(note)}&cu=INR'
            if company.gst_qr_include_amount and move.amount_total:
                params += f'&am={move.amount_total:.2f}'
            upi_uri = f'upi://pay?{params}'
            move.gst_upi_qr_url = '/report/barcode/?barcode_type=QR&value=%s&width=120&height=120' % quote(upi_uri, safe='')

    # ------------------------------------------------------------------
    # Mandatory GSTIN (seller) / PAN (customer) validation
    # ------------------------------------------------------------------
    gst_missing_fields_warning = fields.Char(compute='_compute_gst_missing_fields_warning', string='GST Compliance Warning')

    def _gst_invoice_applies(self):
        self.ensure_one()
        return (
            self.move_type in ('out_invoice', 'out_refund')
            and self.company_id.account_fiscal_country_id.code == 'IN'
        )

    def _gst_get_missing_mandatory_fields(self):
        self.ensure_one()
        missing = []
        if not self.company_id.vat:
            missing.append(_('Company GSTIN'))
        if not self.company_id.l10n_in_pan:
            missing.append(_('Company PAN Number'))
        if self.partner_id and not self.partner_id.l10n_in_pan:
            missing.append(_('Customer PAN Number'))
        return missing

    @api.depends('company_id.vat', 'partner_id.l10n_in_pan', 'move_type')
    def _compute_gst_missing_fields_warning(self):
        for move in self:
            if not move._gst_invoice_applies():
                move.gst_missing_fields_warning = False
                continue
            missing = move._gst_get_missing_mandatory_fields()
            move.gst_missing_fields_warning = (
                _('Missing mandatory GST information: %s', ', '.join(missing)) if missing else False
            )

    def _post(self, soft=True):
        for move in self:
            if move._gst_invoice_applies():
                missing = move._gst_get_missing_mandatory_fields()
                if missing:
                    raise UserError(_(
                        "Cannot confirm this GST invoice — the following mandatory information is missing:\n"
                        "%(fields)s\n\n"
                        "Company GSTIN is set on Settings > Companies. Customer PAN is set on the customer's contact form.",
                        fields='\n'.join('- %s' % m for m in missing),
                    ))
        return super()._post(soft=soft)
