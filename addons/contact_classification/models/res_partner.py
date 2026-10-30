from odoo import _, api, fields, models

CONTACT_TYPES = [
    ('employee', 'Employee'),
    ('vendor', 'Vendor'),
    ('customer', 'Customer'),
    ('affiliate', 'Affiliate / Commission Partner'),
    ('consultant', 'Consultant'),
    ('other', 'Other'),
]

CUSTOMER_CLASSIFICATIONS = [
    ('b2b', 'B2B'),
    ('b2c_d2c', 'B2C / D2C'),
    ('retailer', 'Retailer'),
    ('distributor', 'Distributor'),
    ('manufacturer', 'Manufacturer'),
    ('wholesaler', 'Wholesaler'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Primary type: what this contact mostly is, used for default layout/filters.
    contact_type = fields.Selection(CONTACT_TYPES, string='Primary Contact Type', tracking=True)
    customer_classification = fields.Selection(CUSTOMER_CLASSIFICATIONS, string='Customer Category')

    # Independent role flags: one contact can be several of these at once
    # (e.g. a company that is both a Customer and a Vendor), instead of
    # needing duplicate contact records per role.
    role_employee = fields.Boolean(string='Employee', tracking=True)
    role_vendor = fields.Boolean(string='Vendor', tracking=True)
    role_customer = fields.Boolean(string='Customer', tracking=True)
    role_affiliate = fields.Boolean(string='Affiliate / Commission Partner', tracking=True)
    role_consultant = fields.Boolean(string='Consultant', tracking=True)
    role_other = fields.Boolean(string='Other', tracking=True)

    @api.onchange('contact_type')
    def _onchange_contact_type_set_role(self):
        role_field = 'role_%s' % self.contact_type if self.contact_type else False
        if role_field and role_field in self._fields:
            self[role_field] = True

    affiliate_id = fields.Many2one(
        'sale.affiliate', string='Affiliate Profile', compute='_compute_affiliate_id')

    # Affiliate tab: read-only display of the linked sale.affiliate record's
    # commission data, so it's visible without leaving the contact. Editing
    # happens on the Affiliate Profile record itself (via the smart button).
    affiliate_referral_code = fields.Char(related='affiliate_id.affiliate_param_url', string='Referral Link')
    affiliate_commission_rate = fields.Float(related='affiliate_id.commission_rate', string='Commission %')
    affiliate_total_commission = fields.Monetary(
        related='affiliate_id.total_commission', string='Total Commission', currency_field='partner_currency_id')
    affiliate_paid_commission = fields.Monetary(
        related='affiliate_id.paid_commission', string='Paid Out', currency_field='partner_currency_id')
    affiliate_pending_commission = fields.Monetary(
        related='affiliate_id.pending_commission', string='Pending Payout', currency_field='partner_currency_id')

    # Employee tab: read-only display of non-sensitive hr.employee fields, for
    # a quick look without leaving the contact. Salary, bank, identity
    # documents, payroll, attendance and leave stay on hr.employee itself
    # (fetched via the smart button) so Odoo's native HR security groups
    # (hr.group_hr_user and payroll-specific groups) keep protecting them -
    # duplicating them here would leak them to anyone who can read a contact.
    consultant_service_description = fields.Text(string='Service Details')
    consultant_contract_start = fields.Date(string='Contract Start')
    consultant_contract_end = fields.Date(string='Contract End')
    consultant_billing_rate = fields.Monetary(string='Billing Rate', currency_field='partner_currency_id')

    # Vendor / Customer tab: identifiers not tracked anywhere else in Odoo.
    vendor_code = fields.Char(string='Vendor Code')
    customer_code = fields.Char(string='Customer Code')
    gst_principal_place_of_business = fields.Char(string='Principal Place of Business')
    preferred_payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('other', 'Other'),
    ], string='Preferred Payment Method')
    partner_currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id.id)
    sale_team_id = fields.Many2one('crm.team', string='Sales Team')

    payment_count = fields.Integer(compute='_compute_payment_count')

    def _compute_payment_count(self):
        payment_data = self.env['account.payment']._read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['__count'])
        counts = {partner.id: count for partner, count in payment_data}
        for partner in self:
            partner.payment_count = counts.get(partner.id, 0)

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments'),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    @api.depends()
    def _compute_affiliate_id(self):
        affiliates = self.env['sale.affiliate'].search([('partner_id', 'in', self.ids)])
        by_partner = {a.partner_id.id: a for a in affiliates}
        for partner in self:
            partner.affiliate_id = by_partner.get(partner.id, False)

    def action_view_affiliate(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.affiliate',
            'view_mode': 'form',
            'target': 'current',
        }
        if self.affiliate_id:
            action['res_id'] = self.affiliate_id.id
        else:
            action['context'] = {'default_partner_id': self.id, 'default_name': self.name}
        return action
