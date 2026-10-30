import base64
import hashlib
import hmac

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.wrappers import Response

from odoo import fields, http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class MeetingController(http.Controller):
    @staticmethod
    def _twilio_request_valid():
        token = request.env['ir.config_parameter'].sudo().get_param('meeting_guest_access.dialin_auth_token', '')
        signature = request.httprequest.headers.get('X-Twilio-Signature', '')
        if not token or not signature:
            return False
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        url = base_url + request.httprequest.path
        values = ''.join(
            key + value
            for key in sorted(request.httprequest.form.keys())
            for value in request.httprequest.form.getlist(key)
        )
        digest = hmac.new(token.encode(), (url + values).encode(), hashlib.sha1).digest()
        expected = base64.b64encode(digest).decode()
        return hmac.compare_digest(expected, signature)
    @http.route('/meeting/credentials', type='json', auth='user', methods=['POST'])
    def meeting_credentials(self, channel_id):
        channel = request.env['discuss.channel'].browse(int(channel_id)).exists()
        if not channel or channel.create_uid != request.env.user:
            raise NotFound()
        channel._ensure_meeting_credentials()
        dialin_enabled = channel._dialin_enabled() and bool(channel._dialin_number())
        return {
            'meeting_id': channel.meeting_id,
            'password': channel.meeting_password,
            'invitation_url': channel.invitation_url,
            'expires_at': fields.Datetime.to_string(channel.meeting_expires_at),
            'open': channel.meeting_open,
            'dialin_enabled': dialin_enabled,
            'dialin_number': channel._dialin_number() if dialin_enabled else False,
            'dialin_pin': channel.dialin_pin if dialin_enabled else False,
            'dialin_instructions': 'Call the number and enter this PIN when prompted.' if dialin_enabled else False,
        }

    @http.route('/meeting/close', type='json', auth='user', methods=['POST'])
    def close_meeting(self, channel_id):
        channel = request.env['discuss.channel'].browse(int(channel_id)).exists()
        if not channel or channel.create_uid != request.env.user:
            raise NotFound()
        channel.write({'meeting_open': False})
        return {'open': False}

    @http.route('/meeting/open', type='json', auth='user', methods=['POST'])
    def open_meeting(self, channel_id):
        channel = request.env['discuss.channel'].browse(int(channel_id)).exists()
        if not channel or channel.create_uid != request.env.user:
            raise NotFound()
        channel.write({'meeting_open': True})
        return {'open': True}

    @http.route('/meeting/pending', type='json', auth='user', methods=['POST'])
    def pending_guests(self, channel_id):
        channel = request.env['discuss.channel'].browse(int(channel_id)).exists()
        if not channel or channel.create_uid != request.env.user:
            raise NotFound()
        members = channel.channel_member_ids.filtered(lambda m: m.guest_id and m.meeting_admission_pending)
        return [{'id': m.id, 'name': m.guest_id.name} for m in members]

    @http.route('/meeting/admit', type='json', auth='user', methods=['POST'])
    def admit_guest(self, channel_id, member_id):
        channel = request.env['discuss.channel'].browse(int(channel_id)).exists()
        member = request.env['discuss.channel.member'].browse(int(member_id)).exists()
        if not channel or channel.create_uid != request.env.user or not member or member.channel_id != channel:
            raise NotFound()
        member.write({'meeting_admission_pending': False})
        member._bus_send('meeting_guest/admitted', {'channelId': channel.id})
        return {'admitted': True}

    @http.route('/meeting/join', type='http', auth='public', methods=['GET'], website=True)
    def meeting_join_page(self, error=None, **kwargs):
        return request.render('meeting_guest_access.meeting_join_page', {'error': error})

    @http.route('/meeting/join/validate', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    @add_guest_to_context
    def meeting_join_validate(self, meeting_id, password, guest_name, **kwargs):
        channel = request.env['discuss.channel'].sudo().search([('meeting_id', '=', (meeting_id or '').strip().upper())], limit=1)
        if not channel or not channel.meeting_open or not channel._meeting_is_joinable() or not channel._meeting_credentials_valid(password or ''):
            return request.redirect('/meeting/join?error=invalid')
        guest_name = (guest_name or '').strip()
        if not guest_name or len(guest_name) > 512:
            return request.redirect('/meeting/join?error=name')
        _partner, guest = channel._find_or_create_persona_for_channel(
            guest_name=guest_name,
            timezone=request.env['mail.guest']._get_timezone_from_request(request),
            country_code=request.geoip.country_code,
        )
        if not guest:
            return request.redirect('/meeting/join?error=invalid')
        member = request.env['discuss.channel.member'].sudo().search([
            ('channel_id', '=', channel.id), ('guest_id', '=', guest.id),
        ], limit=1)
        member.write({'meeting_admission_pending': True})
        return request.redirect('/meeting/wait/%s' % channel.uuid)

    @http.route('/meeting/wait/<string:meeting_token>', type='http', auth='public', methods=['GET'], website=True)
    @add_guest_to_context
    def meeting_wait(self, meeting_token, **kwargs):
        channel = request.env['discuss.channel'].sudo().search([('uuid', '=', meeting_token)], limit=1)
        guest = request.env['mail.guest']._get_guest_from_context()
        if not channel or not guest or not channel._meeting_is_joinable():
            return request.redirect('/meeting/join?error=invalid')
        return request.render('meeting_guest_access.meeting_wait_page', {'channel': channel})

    @http.route('/meeting/status/<string:meeting_token>', type='json', auth='public', methods=['POST'])
    @add_guest_to_context
    def meeting_status(self, meeting_token):
        channel = request.env['discuss.channel'].sudo().search([('uuid', '=', meeting_token)], limit=1)
        guest = request.env['mail.guest']._get_guest_from_context()
        if not channel or not guest or not channel._meeting_is_joinable():
            return {'state': 'invalid'}
        if not channel.meeting_open:
            return {'state': 'closed'}
        # Use the existing Discuss invitation route.  The /meet/<uuid> route
        # is optional in Odoo and returns 404 when mail.chat_from_token is
        # disabled, while the invitation URL is the supported public entry
        # point and still opens the existing video call UI.
        return {
            'state': 'admitted' if channel._meeting_guest_can_join(guest) else 'pending',
            'url': channel.invitation_url,
        }

    @staticmethod
    def _twiml(body):
        return Response('<?xml version="1.0" encoding="UTF-8"?>' + body, content_type='text/xml; charset=utf-8')

    @http.route('/meeting/dialin/voice', type='http', auth='public', methods=['POST'], csrf=False)
    def dialin_voice(self, **kwargs):
        """Initial TwiML webhook for the shared dial-in number."""
        enabled = request.env['ir.config_parameter'].sudo().get_param('meeting_guest_access.dialin_enabled', 'False').lower() in ('1', 'true', 'yes')
        if not enabled:
            return self._twiml('<Response><Say>This dial-in service is not enabled.</Say><Hangup/></Response>')
        if not self._twilio_request_valid():
            raise Forbidden('Invalid voice provider signature.')
        return self._twiml(
            '<Response><Gather input="dtmf" numDigits="6" timeout="10" action="/meeting/dialin/verify" method="POST">'
            '<Say>Enter the six digit meeting PIN, followed by the pound key.</Say>'
            '</Gather><Say>No PIN was received.</Say><Hangup/></Response>'
        )

    @http.route('/meeting/dialin/verify', type='http', auth='public', methods=['POST'], csrf=False)
    def dialin_verify(self, **kwargs):
        """Verify a meeting PIN and place the caller into its provider conference."""
        if not self._twilio_request_valid():
            raise Forbidden('Invalid voice provider signature.')
        pin = (request.httprequest.form.get('Digits') or '').strip()
        channel = request.env['discuss.channel'].sudo().search([('dialin_pin', '=', pin)], limit=1)
        if not channel or not channel._meeting_is_joinable() or not channel.meeting_open:
            return self._twiml('<Response><Say>That meeting PIN is invalid or the meeting is closed.</Say><Hangup/></Response>')
        conference = channel.dialin_conference_name or f'odoo-{channel.uuid}'
        return self._twiml(
            '<Response><Say>You are joining the meeting now.</Say><Dial>'
            '<Conference beep="true" startConferenceOnEnter="false" endConferenceOnExit="false">%s</Conference>'
            '</Dial></Response>' % conference
        )
