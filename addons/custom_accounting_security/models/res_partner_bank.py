from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    # View restrictions alone do not protect RPC/read access.  These field
    # groups make account numbers and holder names unavailable to ordinary
    # accounting users and auditors at the ORM field level as required by the
    # security matrix.
    acc_number = fields.Char(groups='custom_accounting_security.group_accounting_finance_controller')
    acc_holder_name = fields.Char(groups='custom_accounting_security.group_accounting_finance_controller')
