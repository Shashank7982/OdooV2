from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

EXPENSE_TYPES = [
    ('vendor', 'Vendor Expense'),
    ('office', 'Office Expense'),
    ('purchase', 'Purchase Expense'),
    ('other', 'Other Expense'),
]

# Expense types that normally involve an outside vendor (vendor field shown).
VENDOR_TYPES = ('vendor', 'office', 'purchase')

PAYMENT_METHODS = [
    ('bank_transfer', 'Bank Transfer'),
    ('cheque', 'Cheque'),
    ('upi', 'UPI'),
    ('cash', 'Cash'),
    ('card', 'Card'),
    ('other', 'Other'),
]


class ExpenseEntry(models.Model):
    _name = 'custom.expense.entry'
    _description = 'Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    expense_type = fields.Selection(EXPENSE_TYPES, string='Expense Type', required=True, default='other', tracking=True)
    date = fields.Date(string='Expense Date', required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)

    partner_id = fields.Many2one(
        'res.partner', string='Vendor',
        domain="[('company_id', 'in', (company_id, False))]")
    description = fields.Char(string='Expense Description', required=True)
    account_id = fields.Many2one(
        'account.account', string='Expense Account', required=True,
        domain="[('account_type', 'in', ('expense', 'expense_depreciation', 'expense_direct_cost')), ('company_ids', '=', company_id)]")
    amount = fields.Monetary(string='Amount', required=True)
    tax_ids = fields.Many2many('account.tax', string='Tax / GST', domain="[('type_tax_use', '=', 'purchase')]")
    payment_method = fields.Selection(PAYMENT_METHODS, string='Payment Method')
    analytic_distribution = fields.Json(string='Analytic Account')

    receipt = fields.Binary(string='Receipt Attachment')
    receipt_filename = fields.Char()

    # For expense types with no vendor/employee to bill against (e.g. Other
    # Expense with neither set): the account credited/paid from, so Post can
    # create a balanced journal entry instead of a vendor bill.
    counterpart_account_id = fields.Many2one(
        'account.account', string='Paid From / Payable Account',
        domain="[('company_ids', '=', company_id)]",
        help="Bank, Cash, or a payable account - required to post this expense "
             "when there's no Vendor or Employee to bill against.")

    # Vendor Expense
    vendor_bill_ref = fields.Char(string='Vendor Bill Reference')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')

    # Purchase Expense
    purchase_order_ref = fields.Char(string='Purchase Order / Reference')
    product_id = fields.Many2one('product.product', string='Product or Service')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('posted', 'Posted'),
    ], string='Approval Status', default='draft', required=True, tracking=True, copy=False)

    move_id = fields.Many2one('account.move', string='Journal Entry / Bill', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.expense.entry') or 'New'
        return super().create(vals_list)

    def _resolve_billing_partner(self):
        """ Vendor for vendor/office/purchase types; the employee's own
        contact (work_contact_id) for salary/reimbursement/travel - salary and
        reimbursements are money owed TO the employee, so billing against
        bill instead of a guessed manual journal entry. """
        self.ensure_one()
        if self.expense_type in VENDOR_TYPES and self.partner_id:
            return self.partner_id
        return self.env['res.partner']

    @api.constrains('amount')
    def _check_amount(self):
        for expense in self:
            if not expense.amount:
                raise ValidationError(_("Amount cannot be 0 - enter the actual expense amount."))

    def _check_required_for_type(self):
        self.ensure_one()
        if self.expense_type in VENDOR_TYPES and not self.partner_id:
            raise ValidationError(_("A Vendor is required for a %s.", dict(EXPENSE_TYPES)[self.expense_type]))
        if not self._resolve_billing_partner() and not self.counterpart_account_id:
            raise ValidationError(_(
                "Set a Vendor to bill this against, or a 'Paid From / Payable Account' "
                "so it can be posted as a direct journal entry."))

    def action_submit(self):
        for expense in self:
            if expense.state != 'draft':
                raise UserError(_("Only a draft expense can be submitted."))
            expense._check_required_for_type()
            expense.state = 'submitted'

    def action_approve(self):
        for expense in self:
            if expense.state != 'submitted':
                raise UserError(_("Only a submitted expense can be approved."))
            expense.state = 'approved'

    def action_reject(self):
        for expense in self:
            if expense.state != 'submitted':
                raise UserError(_("Only a submitted expense can be rejected."))
            expense.state = 'rejected'

    def action_reset_to_draft(self):
        for expense in self:
            if expense.state == 'posted':
                raise UserError(_("A posted expense cannot be reset to draft. Reverse its journal entry/bill instead."))
            expense.state = 'draft'

    def action_post(self):
        for expense in self:
            if expense.state != 'approved':
                raise UserError(_("Only an approved expense can be posted."))
            expense._check_required_for_type()
            move = expense._create_move()
            move.action_post()
            expense.write({'move_id': move.id, 'state': 'posted'})

    def _create_move(self):
        self.ensure_one()
        partner = self._resolve_billing_partner()
        if partner:
            return self._create_vendor_bill(partner)
        return self._create_journal_entry()

    def _create_vendor_bill(self, partner):
        self.ensure_one()
        line_vals = {
            'name': self.description,
            'account_id': self.account_id.id,
            'quantity': 1,
            'price_unit': self.amount,
            'tax_ids': [(6, 0, self.tax_ids.ids)],
        }
        if self.product_id:
            line_vals['product_id'] = self.product_id.id

        move_vals = {
            'move_type': 'in_invoice',
            'company_id': self.company_id.id,
            'partner_id': partner.id,
            'invoice_date': self.date,
            'currency_id': self.currency_id.id,
            'ref': self.vendor_bill_ref or self.purchase_order_ref or self.name,
            'invoice_line_ids': [(0, 0, line_vals)],
        }
        if self.payment_term_id:
            move_vals['invoice_payment_term_id'] = self.payment_term_id.id
        return self.env['account.move'].sudo().with_context(skip_accounting_workflow=True).create(move_vals)

    def _create_journal_entry(self):
        self.ensure_one()
        if not self.counterpart_account_id:
            raise ValidationError(_("Set a 'Paid From / Payable Account' to post this as a direct journal entry."))
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'), ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(_("No general journal found for %s.", self.company_id.name))
        return self.env['account.move'].sudo().with_context(skip_accounting_workflow=True).create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'currency_id': self.currency_id.id,
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'name': self.description, 'account_id': self.account_id.id,
                    'debit': self.amount, 'credit': 0.0,
                }),
                (0, 0, {
                    'name': self.description, 'account_id': self.counterpart_account_id.id,
                    'debit': 0.0, 'credit': self.amount,
                }),
            ],
        })

    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
