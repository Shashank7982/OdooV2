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
    line_ids = fields.One2many('custom.sales.contract.line', 'contract_id', string='Contract Lines')
    terms = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.contract') or 'New'
        return super().create(vals_list)

    def action_activate(self):
        for contract in self:
            if contract.end_date and contract.end_date < contract.start_date:
                raise ValidationError(_('Contract end date must be on or after the start date.'))
        self.write({'state': 'active'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_release_order(self):
        orders = self.env['sale.order']
        for contract in self:
            if contract.state != 'active':
                raise UserError(_('Activate the contract before releasing an order.'))
            if not contract.line_ids:
                raise ValidationError(_('Add at least one contract line before releasing an order.'))
            order = self.env['sale.order'].create({
                'partner_id': contract.partner_id.id,
                'company_id': contract.company_id.id,
                'origin': contract.name,
                'custom_contract_id': contract.id,
            })
            order.order_line.create([{
                'order_id': order.id,
                'product_id': line.product_id.id,
                'name': line.description or line.product_id.display_name,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'price_unit': line.price_unit,
            } for line in contract.line_ids])
            orders |= order
        if len(orders) == 1:
            return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'res_id': orders.id, 'view_mode': 'form'}
        return True


class CustomSalesContractLine(models.Model):
    _name = 'custom.sales.contract.line'
    _description = 'Sales Contract Line'

    contract_id = fields.Many2one('custom.sales.contract', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    description = fields.Char()
    quantity = fields.Float(required=True, default=1.0)
    price_unit = fields.Float(required=True)

    @api.constrains('quantity', 'price_unit')
    def _check_values(self):
        for line in self:
            if line.quantity <= 0 or line.price_unit < 0:
                raise ValidationError(_('Contract quantity must be positive and price cannot be negative.'))


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
    line_ids = fields.One2many('custom.sales.scheduling.agreement.line', 'agreement_id', string='Agreement Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.scheduling.agreement') or 'New'
        return super().create(vals_list)

    def action_activate(self):
        for agreement in self:
            if agreement.contract_id and agreement.contract_id.state != 'active':
                raise ValidationError(_('The linked contract must be active before activating the scheduling agreement.'))
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_release_order(self):
        orders = self.env['sale.order']
        for agreement in self:
            if agreement.state != 'active':
                raise UserError(_('Activate the scheduling agreement before releasing an order.'))
            if agreement.validity_date and agreement.validity_date < fields.Date.context_today(self):
                raise ValidationError(_('The scheduling agreement validity date has expired.'))
            if not agreement.line_ids:
                raise ValidationError(_('Add at least one scheduling-agreement line before releasing an order.'))
            order = self.env['sale.order'].create({
                'partner_id': agreement.partner_id.id,
                'company_id': agreement.company_id.id,
                'origin': agreement.name,
                'custom_contract_id': agreement.contract_id.id,
                'custom_scheduling_agreement_id': agreement.id,
            })
            order.order_line.create([{
                'order_id': order.id,
                'product_id': line.product_id.id,
                'name': line.description or line.product_id.display_name,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'price_unit': line.price_unit,
            } for line in agreement.line_ids])
            orders |= order
        if len(orders) == 1:
            return {'type': 'ir.actions.act_window', 'res_model': 'sale.order', 'res_id': orders.id, 'view_mode': 'form'}
        return True


class CustomSchedulingAgreementLine(models.Model):
    _name = 'custom.sales.scheduling.agreement.line'
    _description = 'Sales Scheduling Agreement Line'

    agreement_id = fields.Many2one('custom.sales.scheduling.agreement', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    description = fields.Char()
    quantity = fields.Float(required=True, default=1.0)
    price_unit = fields.Float(required=True)

    @api.constrains('quantity', 'price_unit')
    def _check_values(self):
        for line in self:
            if line.quantity <= 0 or line.price_unit < 0:
                raise ValidationError(_('Scheduling quantity must be positive and price cannot be negative.'))


class CustomSalesReturn(models.Model):
    _name = 'custom.sales.return.request'
    _description = 'Sales Return Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', required=True)
    original_picking_id = fields.Many2one('stock.picking', required=True, domain="[('partner_id', '=', partner_id)]")
    return_picking_id = fields.Many2one('stock.picking', readonly=True, copy=False)
    invoice_id = fields.Many2one(
        'account.move', string='Original Customer Invoice',
        domain="[('move_type', '=', 'out_invoice'), ('partner_id', '=', partner_id), ('state', '=', 'posted')]",
    )
    credit_note_id = fields.Many2one('account.move', string='Credit Note', readonly=True, copy=False)
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
            action = return_wizard.action_create_returns_all()
            picking_id = action.get('res_id')
            request.write({'return_picking_id': picking_id, 'state': 'done'})

    def action_create_credit_note(self):
        for request in self:
            if request.state not in ('approved', 'done'):
                raise UserError(_('Approve the return before creating a credit note.'))
            if request.credit_note_id:
                continue
            if not request.invoice_id:
                raise ValidationError(_('Select the posted customer invoice to credit.'))
            credit_note = request.invoice_id._reverse_moves([{
                'ref': request.name,
                'invoice_date': fields.Date.context_today(self),
            }], cancel=False)
            request.credit_note_id = credit_note.id
        return {
            'type': 'ir.actions.act_window', 'res_model': 'account.move',
            'res_id': self[-1].credit_note_id.id, 'view_mode': 'form',
        }


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
    validated_by = fields.Many2one('res.users', readonly=True, copy=False)
    validated_at = fields.Datetime(readonly=True, copy=False)

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

    def action_validate(self):
        for record in self:
            if record.state not in ('requested', 'received'):
                raise UserError(_('Request the waybill before validating it.'))
            if not record.number:
                raise ValidationError(_('Enter the external waybill number before validation.'))
            record.write({
                'state': 'received', 'validated_by': self.env.user.id,
                'validated_at': fields.Datetime.now(),
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_contract_id = fields.Many2one('custom.sales.contract', check_company=True)
    custom_scheduling_agreement_id = fields.Many2one('custom.sales.scheduling.agreement', check_company=True)
    is_free_of_charge = fields.Boolean(string='Free-of-Charge Order', tracking=True)
    foc_type = fields.Selection([
        ('delivery', 'Delivery free of charge'),
        ('subsequent_delivery', 'Subsequent delivery free of charge'),
    ], string='Free-of-Charge Type', tracking=True)
    foc_reason = fields.Char()

    @api.constrains('is_free_of_charge', 'foc_type')
    def _check_free_of_charge_configuration(self):
        for order in self:
            if order.is_free_of_charge and not order.foc_type:
                raise ValidationError(_('Select whether this is a delivery or subsequent free-of-charge order.'))

    def action_confirm(self):
        for order in self:
            if order.custom_contract_id and order.custom_contract_id.state != 'active':
                raise ValidationError(_('The linked sales contract must be active before confirmation.'))
            if order.custom_scheduling_agreement_id and order.custom_scheduling_agreement_id.state != 'active':
                raise ValidationError(_('The linked scheduling agreement must be active before confirmation.'))
            if order.is_free_of_charge:
                order.order_line.filtered(lambda line: line.product_id).write({'price_unit': 0.0})
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_free_of_charge = fields.Boolean(string='Free of Charge')
    foc_reason = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_free_of_charge'):
                vals['price_unit'] = 0.0
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('is_free_of_charge'):
            vals = dict(vals, price_unit=0.0)
        return super().write(vals)

    @api.onchange('is_free_of_charge')
    def _onchange_is_free_of_charge(self):
        for line in self:
            if line.is_free_of_charge:
                line.price_unit = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_waybill_ids = fields.One2many('custom.sales.waybill', 'picking_id')
    is_free_of_charge_delivery = fields.Boolean(related='sale_id.is_free_of_charge', store=True)


class CustomSalesDebitMemo(models.Model):
    _name = 'custom.sales.debit.memo'
    _description = 'Customer Debit Memo'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', required=True)
    original_invoice_id = fields.Many2one(
        'account.move', string='Original Invoice', required=True,
        domain="[('move_type', '=', 'out_invoice'), ('partner_id', '=', partner_id), ('state', '=', 'posted')]",
    )
    amount = fields.Monetary(required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    reason = fields.Text(required=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('posted', 'Posted')], default='draft', tracking=True)
    debit_note_id = fields.Many2one('account.move', readonly=True, copy=False)

    @api.constrains('amount')
    def _check_amount(self):
        for memo in self:
            if memo.amount <= 0:
                raise ValidationError(_('Debit memo amount must be greater than zero.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sales.debit.memo') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for memo in self:
            if memo.state != 'draft':
                raise UserError(_('Only a draft debit memo can be confirmed.'))
            memo.state = 'confirmed'

    def action_post(self):
        for memo in self:
            if memo.state != 'confirmed':
                raise UserError(_('Confirm the debit memo before posting it.'))
            if memo.debit_note_id:
                continue
            source_line = memo.original_invoice_id.invoice_line_ids.filtered(
                lambda line: line.display_type == 'product' and line.product_id
            )[:1]
            if not source_line:
                raise ValidationError(_('The original invoice must contain a product line for the debit memo.'))
            debit_note = self.env['account.move'].create({
                'move_type': 'out_invoice', 'company_id': memo.company_id.id,
                'partner_id': memo.partner_id.id, 'invoice_origin': memo.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': source_line.product_id.id,
                    'name': memo.reason,
                    'quantity': 1,
                    'price_unit': memo.amount,
                    'account_id': source_line.account_id.id,
                    'tax_ids': [(6, 0, source_line.tax_ids.ids)],
                })],
            })
            debit_note.action_post()
            memo.write({'debit_note_id': debit_note.id, 'state': 'posted'})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'account.move',
            'res_id': self[-1].debit_note_id.id, 'view_mode': 'form',
        }
