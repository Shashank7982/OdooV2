from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    meeting_dialin_enabled = fields.Boolean(
        string='Enable meeting dial-in',
        config_parameter='meeting_guest_access.dialin_enabled',
    )
    meeting_dialin_phone_number = fields.Char(
        string='Dial-in phone number',
        help='Voice-capable provider number configured to POST to /meeting/dialin/voice.',
        config_parameter='meeting_guest_access.dialin_phone_number',
    )
    meeting_dialin_provider = fields.Selection(
        [('twilio', 'Twilio / compatible TwiML provider')],
        string='Voice provider', default='twilio',
        config_parameter='meeting_guest_access.dialin_provider',
    )
    meeting_dialin_account_sid = fields.Char(
        string='Provider account SID', config_parameter='meeting_guest_access.dialin_account_sid',
    )
    meeting_dialin_auth_token = fields.Char(
        string='Provider auth token',
        config_parameter='meeting_guest_access.dialin_auth_token',
    )
