from odoo import fields, models


class DiscussChannelMember(models.Model):
    _inherit = 'discuss.channel.member'

    meeting_admission_pending = fields.Boolean(
        string='Meeting Admission Pending', default=False, copy=False,
        groups='base.group_user',
    )
