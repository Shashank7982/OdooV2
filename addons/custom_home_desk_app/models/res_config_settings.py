from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_enterprise_installed = fields.Boolean(string='Is Enterprise Installed', config_parameter='custom_home_desk_app.is_enterprise_installed')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        enterprise_module = self.env['ir.module.module'].search([('name', '=', 'web_enterprise'), ('state', '=', 'installed')])
        res.update(
            is_enterprise_installed=bool(enterprise_module),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
