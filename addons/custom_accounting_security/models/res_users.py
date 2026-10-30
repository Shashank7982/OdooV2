from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    accounting_role_ids = fields.Many2many(
        'res.groups',
        string='Custom Accounting Roles',
        compute='_compute_accounting_role_ids',
        readonly=True,
    )

    @api.depends('groups_id')
    def _compute_accounting_role_ids(self):
        role_categories = self.env.ref(
            'custom_accounting_security.module_category_custom_accounting'
        ) | self.env.ref(
            'custom_accounting_security.module_category_custom_accounting_audit'
        )
        for user in self:
            user.accounting_role_ids = user.groups_id.filtered(
                lambda group: group.category_id in role_categories
            )
