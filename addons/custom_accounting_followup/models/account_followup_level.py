from odoo import fields, models


class AccountFollowupLevel(models.Model):
    _name = 'account.followup.level'
    _description = 'Follow-up Level'
    _order = 'delay_days'

    name = fields.Char(required=True)
    delay_days = fields.Integer(required=True, help="Trigger this level once an invoice is this many days overdue.")
    action = fields.Selection([
        ('email', 'Send Email'),
        ('activity', 'Create Activity'),
        ('both', 'Email + Activity'),
    ], required=True, default='email')
    mail_template_id = fields.Many2one('mail.template')
    activity_type_id = fields.Many2one('mail.activity.type')
    activity_summary = fields.Char(default='Follow up on overdue invoice')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
