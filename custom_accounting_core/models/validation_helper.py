from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountValidationHelper(models.AbstractModel):
    _name = 'account.validation.helper'
    _description = 'Shared Accounting Validation Helpers'

    @api.model
    def check_company(self, record, company_field='company_id'):
        """Ensure record belongs to the current allowed company(ies)."""
        if not record:
            return
        company = record[company_field] if company_field in record._fields else record.env.company
        if company not in self.env.companies:
            raise ValidationError(_("Operation not allowed for company %s") % company.name)

    @api.model
    def check_period_lock(self, date, journal=None):
        """Raise if the period is locked for the given journal (or globally)."""
        self.env['account.move']._check_fiscalyear(date)
        if journal:
            journal._check_period_lock(date)

    @api.model
    def check_partner_active(self, partner):
        if partner and not partner.active:
            raise ValidationError(_("Partner '%s' is archived.") % partner.display_name)

    @api.model
    def check_account_active(self, account):
        if account and not account.active:
            raise ValidationError(_("Account '%s' is archived.") % account.display_name)

    @api.model
    def check_tax_valid(self, tax, date):
        if tax and tax.company_id not in self.env.companies:
            raise ValidationError(_("Tax '%s' belongs to another company.") % tax.name)

    @api.model
    def check_analytic_distribution(self, distribution, required=True):
        if required and not distribution:
            raise ValidationError(_("Analytic distribution is required."))

    @api.model
    def check_duplicate_vendor_bill(self, vendor, ref, journal, date):
        """Return True if a duplicate vendor bill exists according to policy."""
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('partner_id', '=', vendor.id),
            ('ref', '=', ref),
            ('journal_id', '=', journal.id),
            ('date', '=', date),
            ('state', '!=', 'cancel'),
        ]
        return bool(self.env['account.move'].search_count(domain))

    @api.model
    def ensure_balanced_move(self, move, precision_digits=2):
        """Validate that a move is balanced (debit == credit) in company currency."""
        diff = sum(move.line_ids.mapped('debit')) - sum(move.line_ids.mapped('credit'))
        if float_compare(diff, 0.0, precision_digits=precision_digits) != 0:
            raise ValidationError(_("Journal entry is not balanced: debit - credit = %s") % diff)

    @api.model
    def prepare_audit_metadata(self, source_model, source_id, action='create'):
        """Return a dict of audit metadata to write on the move."""
        return {
            'source_model': source_model,
            'source_id': source_id,
            'audit_action': action,
            'audit_user_id': self.env.user.id,
            'audit_timestamp': fields.Datetime.now(),
        }