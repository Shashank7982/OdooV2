from odoo import api, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if 'keep_archives' in fields_list:
            values['keep_archives'] = True
        return values
