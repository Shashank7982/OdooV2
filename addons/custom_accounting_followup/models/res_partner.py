from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    followup_level_id = fields.Many2one('account.followup.level', string='Follow-up Level', readonly=True, copy=False)
    followup_last_date = fields.Date(string='Last Follow-up', readonly=True, copy=False)
    max_overdue_days = fields.Integer(compute='_compute_max_overdue_days')

    def _compute_max_overdue_days(self):
        today = fields.Date.context_today(self)
        for partner in self:
            lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('account_id.account_type', '=', 'asset_receivable'),
                ('move_id.state', '=', 'posted'),
                ('reconciled', '=', False),
            ])
            max_days = 0
            for line in lines:
                if not line.amount_residual:
                    continue
                due_date = line.date_maturity or line.date
                days = (today - due_date).days
                max_days = max(max_days, days)
            partner.max_overdue_days = max_days

    def action_send_followup_now(self):
        for partner in self:
            partner._trigger_followup(force=True)

    def _trigger_followup(self, force=False):
        self.ensure_one()
        if self.max_overdue_days <= 0:
            return
        level = self.env['account.followup.level'].search(
            [('delay_days', '<=', self.max_overdue_days)], order='delay_days desc', limit=1)
        if not level:
            return
        if not force and self.followup_level_id == level and self.followup_last_date == fields.Date.context_today(self):
            return

        if level.action in ('email', 'both') and level.mail_template_id:
            level.mail_template_id.send_mail(self.id, force_send=True)
        if level.action in ('activity', 'both') and level.activity_type_id:
            self.activity_schedule(
                activity_type_id=level.activity_type_id.id,
                summary=level.activity_summary,
                note=_("Follow-up level: %s (%s days overdue)", level.name, self.max_overdue_days),
            )
        self.message_post(body=_(
            "Follow-up triggered: level '%(level)s' (%(days)s days overdue).",
            level=level.name, days=self.max_overdue_days,
        ))
        self.write({'followup_level_id': level.id, 'followup_last_date': fields.Date.context_today(self)})

    def _cron_process_followups(self):
        overdue_partners = self.env['account.move.line'].search([
            ('account_id.account_type', '=', 'asset_receivable'),
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
            ('partner_id', '!=', False),
        ]).partner_id
        for partner in overdue_partners:
            partner._trigger_followup()
