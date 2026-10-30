from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CustomSalesInquiry(models.Model):
    _name = 'custom.sales.inquiry'
    _description = 'Sales Inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)
    partner_id = fields.Many2one('res.partner', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('sent', 'Sent'), ('accepted', 'Accepted'), ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)
    notes = fields.Text()
    line_ids = fields.One2many('custom.sales.inquiry.line', 'inquiry_id', string='Requested Items')
    quotation_id = fields.Many2one('sale.order', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.inquiry') or 'New'
        return super().create(vals_list)

    def action_send(self):
        self.write({'state': 'sent'})

    def action_accept(self):
        for inquiry in self:
            if inquiry.quotation_id:
                inquiry.state = 'accepted'
                continue
            if not inquiry.line_ids:
                raise ValidationError(_('Add at least one requested item before accepting the inquiry.'))
            order = self.env['sale.order'].create({
                'partner_id': inquiry.partner_id.id,
                'company_id': inquiry.company_id.id,
                'origin': inquiry.name,
                'client_order_ref': inquiry.name,
                'note': inquiry.notes,
            })
            for line in inquiry.line_ids:
                product = line.product_id
                order.order_line.create({
                    'order_id': order.id,
                    'product_id': product.id if product else False,
                    'name': line.description or (product.display_name if product else inquiry.name),
                    'product_uom_qty': line.quantity,
                    'product_uom': product.uom_id.id if product else self.env.ref('uom.product_uom_unit').id,
                    'price_unit': line.price_unit,
                })
            inquiry.write({'quotation_id': order.id, 'state': 'accepted'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_view_quotation(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'res_id': self.quotation_id.id, 'view_mode': 'form'}


class CustomSalesInquiryLine(models.Model):
    _name = 'custom.sales.inquiry.line'
    _description = 'Sales Inquiry Line'

    inquiry_id = fields.Many2one('custom.sales.inquiry', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    quantity = fields.Float(required=True, default=1.0)
    price_unit = fields.Float(string='Expected Unit Price')

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Inquiry quantity must be greater than zero.'))


class CustomSalesContract(models.Model):
    _name = 'custom.sales.contract'
    _description = 'Sales Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', required=True)
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date()
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    sale_order_ids = fields.One2many('sale.order', 'custom_contract_id')
    terms = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.contract') or 'New'
        return super().create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class CustomSchedulingAgreement(models.Model):
    _name = 'custom.sales.scheduling.agreement'
    _description = 'Sales Scheduling Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', required=True)
    contract_id = fields.Many2one('custom.sales.contract')
    validity_date = fields.Date()
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed')], default='draft', tracking=True)
    sale_order_ids = fields.One2many('sale.order', 'custom_scheduling_agreement_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.scheduling.agreement') or 'New'
        return super().create(vals_list)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})


class CustomSalesReturn(models.Model):
    _name = 'custom.sales.return.request'
    _description = 'Sales Return Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', required=True)
    original_picking_id = fields.Many2one('stock.picking', required=True, domain="[('partner_id', '=', partner_id)]")
    return_picking_id = fields.Many2one('stock.picking', readonly=True, copy=False)
    reason = fields.Text(required=True)
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('done', 'Done'), ('cancelled', 'Cancelled')], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.return') or 'New'
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_create_return(self):
        for request in self:
            if request.state != 'approved':
                raise UserError(_('Approve the return request first.'))
            if request.return_picking_id:
                continue
            return_wizard = self.env['stock.return.picking'].with_context(
                active_id=request.original_picking_id.id,
                active_ids=request.original_picking_id.ids,
                active_model='stock.picking',
            ).create({})
            return_wizard._onchange_picking_id()
            action = return_wizard.create_returns()
            picking_id = action.get('res_id')
            request.write({'return_picking_id': picking_id, 'state': 'done'})


class CustomSalesWaybill(models.Model):
    _name = 'custom.sales.waybill'
    _description = 'Sales Waybill / E-way Boundary Record'
    _inherit = ['mail.thread']

    name = fields.Char(default='New', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    picking_id = fields.Many2one('stock.picking', required=True)
    partner_id = fields.Many2one(related='picking_id.partner_id', store=True)
    number = fields.Char(string='External Waybill Number')
    state = fields.Selection([('draft', 'Draft'), ('requested', 'Requested'), ('received', 'Received'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    request_payload = fields.Text(help='Payload prepared for the external GST/e-way provider.')
    response_payload = fields.Text(help='Response returned by the external GST/e-way provider.')
    error_message = fields.Text()
    provider = fields.Char(help='External provider name. Portal credentials and API filing remain deployment configuration.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.waybill') or 'New'
        return super().create(vals_list)

    def action_request(self):
        self.write({'state': 'requested'})

    def action_receive(self):
        for record in self:
            if not record.number:
                raise ValidationError(_('Enter the external waybill number before marking it received.'))
        self.write({'state': 'received'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_contract_id = fields.Many2one('custom.sales.contract', check_company=True)
    custom_scheduling_agreement_id = fields.Many2one('custom.sales.scheduling.agreement', check_company=True)
    is_free_of_charge = fields.Boolean(string='Free-of-Charge Order', tracking=True)
    foc_reason = fields.Char()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_free_of_charge = fields.Boolean(string='Free of Charge')
    foc_reason = fields.Char()

    @api.onchange('is_free_of_charge')
    def _onchange_is_free_of_charge(self):
        for line in self:
            if line.is_free_of_charge:
                line.price_unit = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_waybill_ids = fields.One2many('custom.sales.waybill', 'picking_id')
    is_free_of_charge_delivery = fields.Boolean(related='sale_id.is_free_of_charge', store=True)
