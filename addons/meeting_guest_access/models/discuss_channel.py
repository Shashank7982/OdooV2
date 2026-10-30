import hashlib
import hmac
import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    meeting_id = fields.Char(string='Meeting ID', copy=False, readonly=True, index=True, groups='base.group_user')
    meeting_password = fields.Char(string='Meeting Password', copy=False, readonly=True, groups='base.group_user')
    meeting_password_salt = fields.Char(copy=False, readonly=True, groups='base.group_user')
    meeting_password_hash = fields.Char(copy=False, readonly=True, groups='base.group_user')
    meeting_expires_at = fields.Datetime(string='Meeting Expires At', copy=False, readonly=True, groups='base.group_user')
    meeting_closed = fields.Boolean(string='Meeting Closed', copy=False, readonly=True, groups='base.group_user')
    meeting_open = fields.Boolean(string='Meeting Open', copy=False, readonly=True, groups='base.group_user')
    dialin_pin = fields.Char(string='Dial-in PIN', copy=False, readonly=True, index=True, groups='base.group_user')
    dialin_conference_name = fields.Char(string='Dial-in Conference', copy=False, readonly=True, groups='base.group_user')

    _sql_constraints = [
        ('meeting_id_unique', 'UNIQUE(meeting_id)', 'Meeting IDs must be unique.'),
        ('dialin_pin_unique', 'UNIQUE(dialin_pin)', 'Dial-in PINs must be unique.'),
    ]

    @api.model
    def _new_meeting_id(self):
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        return '-'.join(''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))

    @api.model
    def _new_meeting_password(self):
        return secrets.token_urlsafe(16)

    @api.model
    def _new_dialin_pin(self):
        for _attempt in range(100):
            pin = f'{secrets.randbelow(1000000):06d}'
            if not self.search_count([('dialin_pin', '=', pin)]):
                return pin
        raise ValueError('Unable to generate a unique dial-in PIN.')

    @api.model
    def _hash_meeting_password(self, password, salt=None):
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 240000).hex()
        return salt, digest

    def _ensure_meeting_credentials(self):
        for channel in self.filtered(lambda c: c.default_display_mode == 'video_full_screen'):
            if channel.meeting_id and channel.meeting_password_hash:
                continue
            password = self._new_meeting_password()
            salt, digest = self._hash_meeting_password(password)
            channel.write({
                'meeting_id': self._new_meeting_id(),
                'meeting_password': password,
                'meeting_password_salt': salt,
                'meeting_password_hash': digest,
                'meeting_expires_at': fields.Datetime.now() + timedelta(days=1),
                'meeting_closed': False,
                'meeting_open': False,
                'dialin_pin': channel.dialin_pin or self._new_dialin_pin(),
                'dialin_conference_name': channel.dialin_conference_name or f'odoo-{channel.uuid}',
            })
        return self

    def _dialin_number(self):
        return self.env['ir.config_parameter'].sudo().get_param('meeting_guest_access.dialin_phone_number', '')

    def _dialin_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param('meeting_guest_access.dialin_enabled', 'False').lower() in ('1', 'true', 'yes')

    def _meeting_credentials_valid(self, password):
        self.ensure_one()
        if not self.meeting_password_hash or self.meeting_closed:
            return False
        if self.meeting_expires_at and self.meeting_expires_at <= fields.Datetime.now():
            return False
        _salt, digest = self._hash_meeting_password(password, self.meeting_password_salt)
        return hmac.compare_digest(digest, self.meeting_password_hash)

    def _meeting_is_joinable(self):
        self.ensure_one()
        return bool(self.meeting_id and not self.meeting_closed and (not self.meeting_expires_at or self.meeting_expires_at > fields.Datetime.now()))

    def _meeting_guest_can_join(self, guest):
        self.ensure_one()
        member = self.env['discuss.channel.member'].sudo().search([
            ('channel_id', '=', self.id), ('guest_id', '=', guest.id),
        ], limit=1)
        return bool(member and self.meeting_open and not member.meeting_admission_pending)

    def action_open_meeting(self):
        for channel in self:
            if channel.create_uid != self.env.user:
                raise AccessError('Only the meeting host can open admission.')
            channel.write({'meeting_open': True})
        return True

    def action_pause_meeting_admission(self):
        for channel in self:
            if channel.create_uid != self.env.user:
                raise AccessError('Only the meeting host can pause admission.')
            channel.write({'meeting_open': False})
        return True
