from odoo import _, fields, models

from odoo.addons.contact_classification.models.res_partner import (
    CONTACT_TYPES, CUSTOMER_CLASSIFICATIONS,
)


class ResPartnerTypeWizard(models.TransientModel):
    _name = 'res.partner.type.wizard'
    _description = 'Select Contact Type'

    company_type = fields.Selection(
        [('person', 'Individual'), ('company', 'Company')],
        string='Individual or Company', default='company', required=True)
    name = fields.Char(string='Name', required=True)
    contact_type = fields.Selection(CONTACT_TYPES, string='Primary Contact Type', required=True, default='customer')
    customer_classification = fields.Selection(CUSTOMER_CLASSIFICATIONS, string='Customer Category')

    # Multi-role: a contact can be more than one of these at once
    # (e.g. a company that is both a Customer and a Vendor).
    role_employee = fields.Boolean(string='Employee')
    role_vendor = fields.Boolean(string='Vendor')
    role_customer = fields.Boolean(string='Customer')
    role_affiliate = fields.Boolean(string='Affiliate / Commission Partner')
    role_consultant = fields.Boolean(string='Consultant')
    role_other = fields.Boolean(string='Other')

    def action_continue(self):
        self.ensure_one()
        role_field = 'role_%s' % self.contact_type
        roles = {
            'role_employee': self.role_employee,
            'role_vendor': self.role_vendor,
            'role_customer': self.role_customer,
            'role_affiliate': self.role_affiliate,
            'role_consultant': self.role_consultant,
            'role_other': self.role_other,
        }
        roles[role_field] = True

        vals = {
            'name': self.name,
            'is_company': self.company_type == 'company',
            'contact_type': self.contact_type,
            'customer_classification': (
                self.customer_classification if self.contact_type == 'customer' else False),
        }
        vals.update(roles)

        partner = self.env['res.partner'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }
