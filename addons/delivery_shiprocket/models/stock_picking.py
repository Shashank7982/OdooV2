# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

SHIPROCKET_STATUS_MAP = {
    'NEW': 'new',
    'AWB ASSIGNED': 'awb_assigned',
    'PICKUP GENERATED': 'pickup_generated',
    'PICKUP QUEUED': 'pickup_generated',
    'PICKED UP': 'picked_up',
    'IN TRANSIT': 'in_transit',
    'OUT FOR DELIVERY': 'out_for_delivery',
    'DELIVERED': 'delivered',
    'CANCELED': 'cancelled',
    'CANCELLED': 'cancelled',
    'RTO INITIATED': 'rto',
    'RTO DELIVERED': 'rto',
    'UNDELIVERED': 'undelivered',
}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shiprocket_shipment_id = fields.Char(string='Shiprocket Shipment ID', copy=False)
    shiprocket_order_id = fields.Char(string='Shiprocket Order ID', copy=False)
    shiprocket_status = fields.Selection([
        ('new', 'New'),
        ('awb_assigned', 'AWB Assigned'),
        ('pickup_generated', 'Pickup Scheduled'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'),
        ('rto', 'Return To Origin'),
        ('undelivered', 'Undelivered'),
        ('cancelled', 'Cancelled'),
    ], string='Shiprocket Status', copy=False, tracking=True)

    # ------------------------------------------------------------------
    # Label / manifest
    # ------------------------------------------------------------------
    def action_shiprocket_generate_label(self):
        for picking in self:
            if picking.delivery_type != 'shiprocket' or not picking.shiprocket_shipment_id:
                continue
            client = picking.carrier_id._shiprocket_get_client()
            resp = client.generate_label([picking.shiprocket_shipment_id])
            label_url = resp.get('label_url')
            if not label_url:
                continue
            content = client.download_file(label_url)
            self.env['ir.attachment'].create({
                'name': f'{picking.name}_shiprocket_label.pdf',
                'type': 'binary',
                'datas': base64.b64encode(content),
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'mimetype': 'application/pdf',
            })
            picking.message_post(body=_("Shiprocket shipping label generated."))

    def action_shiprocket_generate_manifest(self):
        for picking in self:
            if picking.delivery_type != 'shiprocket' or not picking.shiprocket_shipment_id:
                continue
            client = picking.carrier_id._shiprocket_get_client()
            resp = client.generate_manifest([picking.shiprocket_shipment_id])
            manifest_url = resp.get('manifest_url')
            if not manifest_url:
                continue
            content = client.download_file(manifest_url)
            self.env['ir.attachment'].create({
                'name': f'{picking.name}_shiprocket_manifest.pdf',
                'type': 'binary',
                'datas': base64.b64encode(content),
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'mimetype': 'application/pdf',
            })
            picking.message_post(body=_("Shiprocket manifest generated."))

    # ------------------------------------------------------------------
    # Tracking sync
    # ------------------------------------------------------------------
    def action_shiprocket_sync_tracking(self):
        for picking in self:
            if picking.delivery_type != 'shiprocket' or not picking.carrier_tracking_ref:
                continue
            client = picking.carrier_id._shiprocket_get_client()
            try:
                resp = client.track_by_awb(picking.carrier_tracking_ref)
            except Exception:
                _logger.warning("Shiprocket tracking sync failed for %s", picking.name, exc_info=True)
                continue

            tracking_data = resp.get('tracking_data') or {}
            shipment_track = tracking_data.get('shipment_track') or []
            if not shipment_track:
                continue

            current_status = (shipment_track[0].get('current_status') or '').upper()
            new_status = SHIPROCKET_STATUS_MAP.get(current_status)
            if new_status and new_status != picking.shiprocket_status:
                picking.shiprocket_status = new_status
                picking.message_post(body=_("Shiprocket status updated: %s", current_status.title()))
                if new_status == 'delivered' and picking.state != 'done':
                    picking.message_post(body=_("Shiprocket reports this shipment as delivered."))

    def _cron_shiprocket_sync_tracking(self):
        pickings = self.search([
            ('delivery_type', '=', 'shiprocket'),
            ('carrier_tracking_ref', '!=', False),
            ('shiprocket_status', 'not in', ['delivered', 'cancelled', 'rto']),
            ('state', '=', 'done'),
        ])
        for picking in pickings:
            picking.action_shiprocket_sync_tracking()
