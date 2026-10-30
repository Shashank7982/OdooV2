# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

ITHINK_STATUS_MAP = {
    'PENDING PICKUP': 'booked',
    'MANIFESTED': 'booked',
    'IN TRANSIT': 'in_transit',
    'OUT FOR DELIVERY': 'out_for_delivery',
    'DELIVERED': 'delivered',
    'UNDELIVERED': 'undelivered',
    'RTO': 'rto',
    'RTO IN TRANSIT': 'rto',
    'RTO DELIVERED': 'rto',
    'CANCELLED': 'cancelled',
    'LOST': 'undelivered',
}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ithink_awb_number = fields.Char(string='iThink AWB Number', copy=False)
    ithink_logistic_name = fields.Char(string='iThink Logistics Partner', copy=False)
    ithink_tracking_url = fields.Char(string='iThink Tracking URL', copy=False)
    ithink_status = fields.Selection([
        ('booked', 'Booked'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'),
        ('rto', 'Return To Origin'),
        ('undelivered', 'Undelivered'),
        ('cancelled', 'Cancelled'),
    ], string='iThink Status', copy=False, tracking=True)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('ithink_awb_number'):
            for picking in self:
                if picking.delivery_type == 'ithink' and picking.ithink_awb_number and not picking.carrier_tracking_ref:
                    picking.carrier_tracking_ref = picking.ithink_awb_number
        return res

    # ------------------------------------------------------------------
    # Label / manifest
    # ------------------------------------------------------------------
    def action_ithink_generate_label(self):
        for picking in self:
            if picking.delivery_type != 'ithink' or not picking.ithink_awb_number:
                continue
            client = picking.carrier_id._ithink_get_client()
            resp = client.print_label([picking.ithink_awb_number])
            file_url = resp.get('file_name')
            if not file_url:
                continue
            content = client.download_file(file_url)
            self.env['ir.attachment'].create({
                'name': f'{picking.name}_ithink_label.pdf',
                'type': 'binary',
                'datas': base64.b64encode(content),
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'mimetype': 'application/pdf',
            })
            picking.message_post(body=_("iThink Logistics shipping label generated."))

    def action_ithink_generate_manifest(self):
        for picking in self:
            if picking.delivery_type != 'ithink' or not picking.ithink_awb_number:
                continue
            client = picking.carrier_id._ithink_get_client()
            resp = client.print_manifest([picking.ithink_awb_number])
            file_url = resp.get('file_name')
            if not file_url:
                continue
            content = client.download_file(file_url)
            self.env['ir.attachment'].create({
                'name': f'{picking.name}_ithink_manifest.pdf',
                'type': 'binary',
                'datas': base64.b64encode(content),
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'mimetype': 'application/pdf',
            })
            picking.message_post(body=_("iThink Logistics manifest generated."))

    # ------------------------------------------------------------------
    # Tracking sync
    # ------------------------------------------------------------------
    def action_ithink_sync_tracking(self):
        for picking in self:
            if picking.delivery_type != 'ithink' or not picking.ithink_awb_number:
                continue
            client = picking.carrier_id._ithink_get_client()
            try:
                resp = client.track_order([picking.ithink_awb_number])
            except Exception:
                _logger.warning("iThink Logistics tracking sync failed for %s", picking.name, exc_info=True)
                continue

            track_data = (resp.get('data') or {}).get(picking.ithink_awb_number) or {}
            current_status = (track_data.get('current_status') or '').upper()
            new_status = ITHINK_STATUS_MAP.get(current_status)
            if new_status and new_status != picking.ithink_status:
                picking.ithink_status = new_status
                picking.message_post(body=_("iThink Logistics status updated: %s", current_status.title()))
                if new_status == 'delivered' and picking.state != 'done':
                    picking.message_post(body=_("iThink Logistics reports this shipment as delivered."))

    def _cron_ithink_sync_tracking(self):
        pickings = self.search([
            ('delivery_type', '=', 'ithink'),
            ('ithink_awb_number', '!=', False),
            ('ithink_status', 'not in', ['delivered', 'cancelled', 'rto']),
            ('state', '=', 'done'),
        ])
        for picking in pickings:
            picking.action_ithink_sync_tracking()
