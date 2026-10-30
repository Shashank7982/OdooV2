from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


TRANSACTION_MODES = [
    ('credit', 'Credit transaction'),
    ('cash', 'Cash transaction'),
]

PAYMENT_METHODS = [
    ('cash', 'Cash'),
    ('upi', 'UPI'),
    ('card', 'Card'),
    ('cheque', 'Cheque'),
    ('other', 'Other'),
]


class AccountCashLocation(models.Model):
    _name = 'account.cash.location'
    _description = 'Cash Location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'company_id, name'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, tracking=True)
    journal_id = fields.Many2one(
        'account.journal', string='Cash Journal', required=True,
        domain="[('company_id', '=', company_id), ('type', '=', 'cash')]",
        check_company=True, tracking=True,
    )
    custodian_id = fields.Many2one(
        'res.users', string='Custodian',
        domain="[('company_ids', 'in', company_id)]", tracking=True,
    )
    notes = fields.Text()

    _sql_constraints = [
        ('cash_location_company_name_uniq', 'unique(company_id, name)',
         'Cash location names must be unique per company.'),
    ]

    @api.constrains('journal_id', 'company_id')
    def _check_cash_journal(self):
        for location in self:
            if location.journal_id and (
                location.journal_id.type != 'cash'
                or location.journal_id.company_id != location.company_id
            ):
                raise ValidationError(_('A cash location must use a cash journal from the same company.'))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    transaction_mode = fields.Selection(TRANSACTION_MODES, default='credit', tracking=True)
    cash_journal_id = fields.Many2one(
        'account.journal', string='Cash Journal',
        domain="[('company_id', '=', company_id), ('type', '=', 'cash')]",
        check_company=True, tracking=True,
    )
    cash_location_id = fields.Many2one(
        'account.cash.location', string='Cash Location',
        domain="[('company_id', '=', company_id), ('journal_id', '=', cash_journal_id)]",
        check_company=True, tracking=True,
    )
    cash_payment_method = fields.Selection(PAYMENT_METHODS, string='Payment Method', tracking=True)
    cash_receipt_ref = fields.Char(string='Cash Receipt / Reference', tracking=True)

    @api.constrains('transaction_mode', 'cash_journal_id', 'cash_location_id')
    def _check_cash_order_configuration(self):
        for order in self:
            if order.transaction_mode != 'cash':
                continue
            if not order.cash_journal_id or order.cash_journal_id.type != 'cash':
                raise ValidationError(_('Select an active cash journal for a Cash transaction.'))
            if order.cash_location_id and order.cash_location_id.journal_id != order.cash_journal_id:
                raise ValidationError(_('The cash location must belong to the selected cash journal.'))

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals.update({
            'transaction_mode': self.transaction_mode,
            'cash_journal_id': self.cash_journal_id.id,
            'cash_location_id': self.cash_location_id.id,
            'cash_payment_method': self.cash_payment_method,
            'cash_receipt_ref': self.cash_receipt_ref,
        })
        return vals


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    transaction_mode = fields.Selection(TRANSACTION_MODES, default='credit', tracking=True)
    cash_journal_id = fields.Many2one(
        'account.journal', string='Cash Journal',
        domain="[('company_id', '=', company_id), ('type', '=', 'cash')]",
        check_company=True, tracking=True,
    )
    cash_location_id = fields.Many2one(
        'account.cash.location', string='Cash Location',
        domain="[('company_id', '=', company_id), ('journal_id', '=', cash_journal_id)]",
        check_company=True, tracking=True,
    )
    cash_payment_method = fields.Selection(PAYMENT_METHODS, string='Payment Method', tracking=True)
    cash_receipt_ref = fields.Char(string='Cash Receipt / Reference', tracking=True)

    @api.constrains('transaction_mode', 'cash_journal_id', 'cash_location_id')
    def _check_cash_order_configuration(self):
        for order in self:
            if order.transaction_mode != 'cash':
                continue
            if not order.cash_journal_id or order.cash_journal_id.type != 'cash':
                raise ValidationError(_('Select an active cash journal for a Cash transaction.'))
            if order.cash_location_id and order.cash_location_id.journal_id != order.cash_journal_id:
                raise ValidationError(_('The cash location must belong to the selected cash journal.'))

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals.update({
            'transaction_mode': self.transaction_mode,
            'cash_journal_id': self.cash_journal_id.id,
            'cash_location_id': self.cash_location_id.id,
            'cash_payment_method': self.cash_payment_method,
            'cash_receipt_ref': self.cash_receipt_ref,
        })
        return vals


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_mode = fields.Selection(TRANSACTION_MODES, default='credit', tracking=True, copy=True)
    cash_journal_id = fields.Many2one(
        'account.journal', string='Cash Settlement Journal', copy=True,
        domain="[('company_id', '=', company_id), ('type', '=', 'cash')]",
        check_company=True, tracking=True,
    )
    cash_location_id = fields.Many2one(
        'account.cash.location', string='Cash Location', copy=True,
        domain="[('company_id', '=', company_id), ('journal_id', '=', cash_journal_id)]",
        check_company=True, tracking=True,
    )
    cash_payment_method = fields.Selection(PAYMENT_METHODS, string='Payment Method', copy=True, tracking=True)
    cash_receipt_ref = fields.Char(string='Cash Receipt / Reference', copy=True, tracking=True)
    cash_payment_id = fields.Many2one('account.payment', string='Cash Settlement', readonly=True, copy=False)

    @api.constrains('transaction_mode', 'cash_journal_id', 'cash_location_id', 'company_id')
    def _check_cash_move_configuration(self):
        for move in self:
            if move.transaction_mode != 'cash' or not move.is_invoice(include_receipts=True):
                continue
            move._validate_cash_configuration(require_receipt=False)

    def _validate_cash_configuration(self, require_receipt=True):
        self.ensure_one()
        if self.transaction_mode != 'cash':
            return
        if not self.is_invoice(include_receipts=True):
            raise ValidationError(_('Cash transaction mode is available for invoices, bills and receipts only.'))
        journal = self.cash_journal_id
        if not journal or journal.type != 'cash' or journal.company_id != self.company_id or not journal.active:
            raise ValidationError(_('Select an active cash journal belonging to the same company.'))
        if self.cash_location_id and self.cash_location_id.journal_id != journal:
            raise ValidationError(_('The cash location must belong to the selected cash journal.'))
        if require_receipt and not self.cash_receipt_ref:
            raise ValidationError(_('Cash Receipt / Reference is required for a Cash transaction.'))

    def action_post(self):
        if not self.env.context.get('skip_accounting_workflow'):
            if not self.env.user.has_group('custom_accounting_security.group_accounting_manager'):
                raise UserError(_('Only an Accounting Manager can post an entry.'))
            if any(move.state != 'approved' for move in self):
                raise UserError(_('Only Approved entries can be posted.'))
        cash_moves = self.filtered(lambda move: move.transaction_mode == 'cash' and move.is_invoice(include_receipts=True))
        for move in cash_moves:
            move._validate_cash_configuration(require_receipt=True)
        result = super().action_post()
        for move in cash_moves.filtered(lambda record: record.state == 'posted' and not record.cash_payment_id):
            move._create_cash_settlement()
        return result

    def _create_cash_settlement(self):
        self.ensure_one()
        if self.cash_payment_id or self.move_type in ('entry', 'out_receipt', 'in_receipt'):
            return self.cash_payment_id
        if self.state != 'posted':
            raise UserError(_('The invoice or bill must be posted before cash settlement.'))

        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.ids, active_id=self.id,
        ).create({
            'journal_id': self.cash_journal_id.id,
            'payment_date': self.invoice_date or self.date,
            'communication': self.cash_receipt_ref or self.name,
        })
        payment_register.action_create_payments()
        payment = self.reconciled_payment_ids.filtered(lambda p: p.journal_id == self.cash_journal_id)[-1:]
        if not payment:
            raise UserError(_('The cash payment was created but could not be reconciled with the document.'))
        # Keep the cash dimensions on the settlement move as well as on the
        # invoice.  This makes Cash Book and location-level reconciliation
        # include the actual receipt/payment entry created by Odoo.
        payment.move_id.write({
            'transaction_mode': 'cash',
            'cash_journal_id': self.cash_journal_id.id,
            'cash_location_id': self.cash_location_id.id,
            'cash_payment_method': self.cash_payment_method,
            'cash_receipt_ref': self.cash_receipt_ref,
        })
        self.cash_payment_id = payment.id
        return payment


class PettyCashVoucher(models.Model):
    _name = 'account.petty.cash.voucher'
    _description = 'Petty Cash Voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('posted', 'Posted'),
    ], default='draft', required=True, tracking=True, copy=False)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    location_id = fields.Many2one('account.cash.location', required=True, tracking=True, check_company=True)
    company_id = fields.Many2one(related='location_id.company_id', store=True, readonly=True)
    journal_id = fields.Many2one(related='location_id.journal_id', store=True, readonly=True)
    custodian_id = fields.Many2one(related='location_id.custodian_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Payee', check_company=True)
    payee_name = fields.Char(string='Payee Name')
    purpose = fields.Char(required=True)
    expense_account_id = fields.Many2one(
        'account.account', string='Expense Account', required=True, check_company=True,
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ('expense', 'expense_direct_cost'))]",
    )
    tax_ids = fields.Many2many(
        'account.tax', string='Input GST',
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
    )
    amount = fields.Monetary(required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    receipt = fields.Binary(string='Receipt')
    receipt_filename = fields.Char()
    notes = fields.Text()
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and not self.env.user.has_group('custom_accounting_security.group_accounting_user'):
            raise UserError(_('Only an Accounting User can create Draft cash vouchers.'))
        vals_list = self._assign_names(vals_list)
        return super().create(vals_list)

    def _is_noop_write(self, vals):
        """Allow the unchanged form save sent before a workflow button."""
        if len(self) != 1:
            return False
        for field_name, value in vals.items():
            field = self._fields.get(field_name)
            if not field or field.type in ('one2many', 'many2many'):
                return False
            current = field.convert_to_cache(self[field_name], self)
            incoming = field.convert_to_cache(value, self)
            if field.type == 'many2one':
                current = current.id if current else False
                incoming = incoming.id if incoming else False
            if current != incoming:
                return False
        return True

    def write(self, vals):
        if self.env.context.get('cash_workflow_transition'):
            return super().write(vals)
        is_controller = self.env.user.has_group('custom_accounting_security.group_accounting_finance_controller')
        is_manager = self.env.user.has_group('custom_accounting_security.group_accounting_manager')
        is_cfo = self.env.user.has_group('custom_accounting_security.group_accounting_cfo_admin')
        if (is_controller or is_manager or is_cfo) and self._is_noop_write(vals):
            return super().write(vals)
        if not self.env.su and not self.env.user.has_group('custom_accounting_security.group_accounting_user'):
            raise UserError(_('This role cannot edit cash vouchers.'))
        if any(voucher.state != 'draft' for voucher in self):
            raise UserError(_('Only Draft cash vouchers can be edited.'))
        if 'state' in vals:
            raise UserError(_('Use the workflow buttons to change a cash voucher status.'))
        return super().write(vals)

    def _assign_names(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.petty.cash.voucher') or 'New'
        return vals_list

    @api.constrains('amount')
    def _check_amount(self):
        for voucher in self:
            if voucher.amount <= 0:
                raise ValidationError(_('Petty-cash amount must be greater than zero.'))

    def action_submit(self):
        if not self.env.user.has_group('custom_accounting_security.group_accounting_finance_controller'):
            raise UserError(_('Only a Finance Controller can submit a Draft cash voucher.'))
        for voucher in self:
            if voucher.state != 'draft':
                raise UserError(_('Only a draft voucher can be submitted.'))
            voucher.with_context(cash_workflow_transition=True).write({'state': 'submitted'})

    def action_approve(self):
        if not self.env.user.has_group('custom_accounting_security.group_accounting_manager'):
            raise UserError(_('Only an Accounting Manager can approve a cash voucher.'))
        for voucher in self:
            if voucher.state != 'submitted':
                raise UserError(_('Only a submitted voucher can be approved.'))
            voucher.with_context(cash_workflow_transition=True).write({'state': 'approved'})

    def action_reject(self):
        for voucher in self:
            if voucher.state != 'submitted':
                raise UserError(_('Only a submitted voucher can be rejected.'))
            voucher.state = 'rejected'

    def action_reset_to_draft(self):
        for voucher in self:
            if voucher.state == 'posted':
                raise UserError(_('A posted voucher must be corrected by reversal or adjustment.'))
            voucher.state = 'draft'

    def _tax_line_values(self):
        self.ensure_one()
        if not self.tax_ids:
            return [], self.amount
        tax_result = self.tax_ids.compute_all(
            self.amount, currency=self.currency_id, quantity=1, product=False, partner=self.partner_id,
        )
        values = []
        for tax_value in tax_result.get('taxes', []):
            tax = self.env['account.tax'].browse(tax_value['id'])
            repartition = tax.invoice_repartition_line_ids.filtered(
                lambda line: line.repartition_type == 'tax' and line.account_id
            )[:1]
            if not repartition:
                raise ValidationError(_('Tax %s has no tax account configured.') % tax.display_name)
            values.append({
                'name': tax.name, 'account_id': repartition.account_id.id,
                'debit': tax_value['amount'], 'credit': 0.0, 'tax_line_id': tax.id,
            })
        return values, tax_result['total_included']

    def _create_move(self):
        self.ensure_one()
        journal = self.journal_id
        cash_account = journal.default_account_id
        if not cash_account or cash_account.account_type != 'asset_cash':
            raise ValidationError(_('Configure an asset cash default account on the petty-cash journal.'))
        tax_lines, total = self._tax_line_values()
        lines = [{
            'name': self.purpose, 'account_id': self.expense_account_id.id,
            'partner_id': self.partner_id.id, 'debit': self.amount, 'credit': 0.0,
        }]
        lines.extend(tax_lines)
        lines.append({
            'name': self.purpose, 'account_id': cash_account.id,
            'partner_id': self.partner_id.id, 'debit': 0.0, 'credit': total,
        })
        return self.env['account.move'].sudo().with_context(skip_accounting_workflow=True).create({
            'move_type': 'entry', 'journal_id': journal.id, 'company_id': self.company_id.id,
            'date': self.date, 'ref': self.name, 'transaction_mode': 'cash',
            'cash_journal_id': journal.id, 'cash_location_id': self.location_id.id,
            'cash_payment_method': 'cash', 'cash_receipt_ref': self.name,
            'line_ids': [(0, 0, values) for values in lines],
        })

    def action_post(self):
        if not self.env.user.has_group('custom_accounting_security.group_accounting_manager'):
            raise UserError(_('Only an Accounting Manager can post a cash voucher.'))
        for voucher in self:
            if voucher.state != 'approved':
                raise UserError(_('Only an approved petty-cash voucher can be posted.'))
            move = voucher._create_move()
            move.with_context(skip_accounting_workflow=True).action_post()
            voucher.with_context(cash_workflow_transition=True).write({'move_id': move.id, 'state': 'posted'})

    def action_view_move(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': self.move_id.id, 'view_mode': 'form'}


class PettyCashCount(models.Model):
    _name = 'account.petty.cash.count'
    _description = 'Petty Cash Physical Count'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'count_date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    location_id = fields.Many2one('account.cash.location', required=True, check_company=True, tracking=True)
    company_id = fields.Many2one(related='location_id.company_id', store=True, readonly=True)
    journal_id = fields.Many2one(related='location_id.journal_id', store=True, readonly=True)
    count_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    counted_amount = fields.Monetary(required=True, currency_field='currency_id')
    book_balance = fields.Monetary(compute='_compute_balances', currency_field='currency_id')
    variance = fields.Monetary(compute='_compute_balances', currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved')], default='draft', tracking=True)
    variance_account_id = fields.Many2one(
        'account.account', string='Variance Account', check_company=True,
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ('expense', 'income_other'))]",
    )
    adjustment_move_id = fields.Many2one('account.move', readonly=True, copy=False)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.petty.cash.count') or 'New'
        return super().create(vals_list)

    @api.depends('location_id', 'count_date', 'counted_amount')
    def _compute_balances(self):
        for count in self:
            if not count.journal_id or not count.journal_id.default_account_id:
                count.book_balance = 0.0
            else:
                lines = self.env['account.move.line'].search([
                    ('company_id', '=', count.company_id.id),
                    ('account_id', '=', count.journal_id.default_account_id.id),
                    ('move_id.state', '=', 'posted'), ('date', '<=', count.count_date),
                ])
                count.book_balance = sum(lines.mapped('debit')) - sum(lines.mapped('credit'))
            count.variance = count.counted_amount - count.book_balance

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_create_adjustment(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Approve the physical count before creating an adjustment.'))
        if self.adjustment_move_id or not self.variance:
            return self.adjustment_move_id
        if not self.variance_account_id:
            raise ValidationError(_('Select a variance account before creating an adjustment.'))
        general = self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id), ('type', '=', 'general'),
        ], limit=1)
        if not general:
            raise UserError(_('No general journal is configured for the cash variance adjustment.'))
        amount = abs(self.variance)
        cash_account = self.journal_id.default_account_id
        if self.variance < 0:
            lines = [
                (0, 0, {'name': self.name, 'account_id': self.variance_account_id.id, 'debit': amount, 'credit': 0.0}),
                (0, 0, {'name': self.name, 'account_id': cash_account.id, 'debit': 0.0, 'credit': amount}),
            ]
        else:
            lines = [
                (0, 0, {'name': self.name, 'account_id': cash_account.id, 'debit': amount, 'credit': 0.0}),
                (0, 0, {'name': self.name, 'account_id': self.variance_account_id.id, 'debit': 0.0, 'credit': amount}),
            ]
        move = self.env['account.move'].sudo().with_context(skip_accounting_workflow=True).create({
            'move_type': 'entry', 'journal_id': general.id, 'company_id': self.company_id.id,
            'date': self.count_date, 'ref': self.name, 'transaction_mode': 'cash',
            'cash_journal_id': self.journal_id.id, 'cash_location_id': self.location_id.id,
            'cash_receipt_ref': self.name, 'line_ids': lines,
        })
        move.action_post()
        self.adjustment_move_id = move.id
        return move


class CashBookReportWizard(models.TransientModel):
    _name = 'cash.book.report.wizard'
    _description = 'Cash Book Report'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1, month=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    journal_ids = fields.Many2many('account.journal', string='Cash Journals', domain="[('company_id', '=', company_id), ('type', '=', 'cash')]")
    location_id = fields.Many2one('account.cash.location', domain="[('company_id', '=', company_id)]")
    transaction_mode = fields.Selection([('all', 'All'), *TRANSACTION_MODES], default='all', required=True)
    line_ids = fields.One2many('cash.book.report.line', 'wizard_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    total_receipts = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_payments = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    closing_balance = fields.Monetary(compute='_compute_totals', currency_field='currency_id')

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_receipts = sum(wizard.line_ids.mapped('debit'))
            wizard.total_payments = sum(wizard.line_ids.mapped('credit'))
            wizard.closing_balance = wizard.total_receipts - wizard.total_payments

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [
            ('company_id', '=', self.company_id.id), ('date', '>=', self.date_from),
            ('date', '<=', self.date_to), ('move_id.state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_cash'),
        ]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.location_id:
            domain.append(('move_id.cash_location_id', '=', self.location_id.id))
        if self.transaction_mode != 'all':
            domain.append(('move_id.transaction_mode', '=', self.transaction_mode))
        lines = self.env['account.move.line'].search(domain, order='date, id')
        running = 0.0
        vals = []
        for line in lines:
            running += line.debit - line.credit
            vals.append({
                'wizard_id': self.id, 'date': line.date, 'journal_id': line.journal_id.id,
                'location_id': line.move_id.cash_location_id.id, 'move_id': line.move_id.id,
                'partner_id': line.partner_id.id, 'account_id': line.account_id.id,
                'transaction_mode': line.move_id.transaction_mode,
                'reference': line.move_id.cash_receipt_ref or line.move_id.ref or line.move_id.name,
                'debit': line.debit, 'credit': line.credit, 'balance': line.debit - line.credit,
                'running_balance': running,
            })
        self.env['cash.book.report.line'].create(vals)
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new'}


class CashBookReportLine(models.TransientModel):
    _name = 'cash.book.report.line'
    _description = 'Cash Book Report Line'
    _order = 'date, id'

    wizard_id = fields.Many2one('cash.book.report.wizard', required=True, ondelete='cascade')
    date = fields.Date()
    journal_id = fields.Many2one('account.journal')
    location_id = fields.Many2one('account.cash.location')
    move_id = fields.Many2one('account.move')
    partner_id = fields.Many2one('res.partner')
    account_id = fields.Many2one('account.account')
    transaction_mode = fields.Selection(TRANSACTION_MODES)
    reference = fields.Char()
    debit = fields.Monetary(currency_field='currency_id')
    credit = fields.Monetary(currency_field='currency_id')
    balance = fields.Monetary(currency_field='currency_id')
    running_balance = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    def action_view_move(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': self.move_id.id, 'view_mode': 'form'}


class PettyCashReportWizard(models.TransientModel):
    _name = 'petty.cash.report.wizard'
    _description = 'Petty Cash Report'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1, month=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    location_id = fields.Many2one('account.cash.location', domain="[('company_id', '=', company_id)]")
    custodian_id = fields.Many2one('res.users')
    line_ids = fields.One2many('petty.cash.report.line', 'wizard_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    total_amount = fields.Monetary(compute='_compute_total', currency_field='currency_id')

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.line_ids.mapped('amount'))

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [
            ('company_id', '=', self.company_id.id), ('state', '=', 'posted'),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
        ]
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        if self.custodian_id:
            domain.append(('custodian_id', '=', self.custodian_id.id))
        vouchers = self.env['account.petty.cash.voucher'].search(domain, order='date, id')
        self.env['petty.cash.report.line'].create([{
            'wizard_id': self.id, 'date': v.date, 'voucher_id': v.id,
            'location_id': v.location_id.id, 'custodian_id': v.custodian_id.id,
            'payee': v.payee_name or v.partner_id.name, 'purpose': v.purpose,
            'amount': v.amount, 'state': v.state, 'move_id': v.move_id.id,
        } for v in vouchers])
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new'}


class PettyCashReportLine(models.TransientModel):
    _name = 'petty.cash.report.line'
    _description = 'Petty Cash Report Line'
    _order = 'date, id'

    wizard_id = fields.Many2one('petty.cash.report.wizard', required=True, ondelete='cascade')
    date = fields.Date()
    voucher_id = fields.Many2one('account.petty.cash.voucher')
    location_id = fields.Many2one('account.cash.location')
    custodian_id = fields.Many2one('res.users')
    payee = fields.Char()
    purpose = fields.Char()
    amount = fields.Monetary(currency_field='currency_id')
    state = fields.Selection(related='voucher_id.state')
    move_id = fields.Many2one('account.move')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    def action_view_voucher(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.petty.cash.voucher', 'res_id': self.voucher_id.id, 'view_mode': 'form'}
