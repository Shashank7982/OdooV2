from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_custom_desk = fields.Boolean(string='Custom Desk Product', help='Requires a desk configuration before a sale order is confirmed.')


class CustomDeskConfiguration(models.Model):
    _name = 'custom.desk.configuration'
    _description = 'Custom Desk Configuration'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', ondelete='set null')
    product_tmpl_id = fields.Many2one('product.template', string='Desk Product', required=True, domain="[('is_custom_desk', '=', True)]")
    width_mm = fields.Float(string='Width (mm)', required=True)
    depth_mm = fields.Float(string='Depth (mm)', required=True)
    height_mm = fields.Float(string='Height (mm)', required=True)
    material = fields.Char()
    finish = fields.Char()
    cable_tray = fields.Boolean(string='Cable Tray')
    drawer_count = fields.Integer(string='Drawer Count', default=0)
    price_adjustment = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    notes = fields.Text()
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('cancelled', 'Cancelled')], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.desk.configuration') or 'New'
        return super().create(vals_list)

    @api.constrains('width_mm', 'depth_mm', 'height_mm', 'drawer_count')
    def _check_dimensions(self):
        for record in self:
            if min(record.width_mm, record.depth_mm, record.height_mm) <= 0:
                raise ValidationError(_('Desk width, depth, and height must be greater than zero.'))
            if record.drawer_count < 0:
                raise ValidationError(_('Drawer count cannot be negative.'))

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    desk_configuration_id = fields.Many2one('custom.desk.configuration', string='Desk Configuration', copy=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:
            missing = order.order_line.filtered(
                lambda line: line.product_id.product_tmpl_id.is_custom_desk and not line.desk_configuration_id
            )
            if missing:
                raise ValidationError(_(
                    'A desk configuration is required for custom desk lines: %s',
                    ', '.join(missing.mapped('name')),
                ))
            unapproved = order.order_line.filtered(
                lambda line: line.desk_configuration_id and line.desk_configuration_id.state != 'approved'
            )
            if unapproved:
                raise ValidationError(_('Approve every desk configuration before confirming the sales order.'))
        return super().action_confirm()
