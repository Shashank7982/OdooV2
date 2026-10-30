from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CustomPurchaseRequest(models.Model):
    _name = 'custom.purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    vendor_id = fields.Many2one('res.partner', domain="[('supplier_rank', '>', 0)]")
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('ordered', 'RFQ Created'),
    ], default='draft', required=True, tracking=True)
    notes = fields.Text()
    line_ids = fields.One2many('custom.purchase.request.line', 'request_id')
    purchase_order_id = fields.Many2one('purchase.order', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.purchase.request') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for request in self:
            if not request.line_ids:
                raise ValidationError(_('Add at least one requested item before submitting.'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_create_rfq(self):
        for request in self:
            if request.state != 'approved':
                raise UserError(_('Approve the purchase request before creating an RFQ.'))
            if request.purchase_order_id:
                continue
            if not request.vendor_id:
                raise ValidationError(_('Select a vendor before creating the RFQ.'))
            order = self.env['purchase.order'].create({
                'partner_id': request.vendor_id.id,
                'company_id': request.company_id.id,
                'origin': request.name,
            })
            for line in request.line_ids:
                product = line.product_id
                order.order_line.create({
                    'order_id': order.id,
                    'product_id': product.id if product else False,
                    'name': line.description or (product.display_name if product else request.name),
                    'product_qty': line.quantity,
                    'product_uom': product.uom_po_id.id if product else self.env.ref('uom.product_uom_unit').id,
                    'price_unit': line.price_unit,
                    'date_planned': request.date,
                })
            request.write({'purchase_order_id': order.id, 'state': 'ordered'})


class CustomPurchaseRequestLine(models.Model):
    _name = 'custom.purchase.request.line'
    _description = 'Purchase Request Line'

    request_id = fields.Many2one('custom.purchase.request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    quantity = fields.Float(required=True, default=1.0)
    price_unit = fields.Float(string='Expected Unit Price')

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Purchase request quantity must be greater than zero.'))


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    custom_purchase_request_id = fields.Many2one('custom.purchase.request', check_company=True)
    goods_available = fields.Boolean(string='Goods Available', copy=False)
    backorder_required = fields.Boolean(string='Backorder Required', copy=False)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    source_purchase_request_id = fields.Many2one(related='purchase_id.custom_purchase_request_id', store=True)
