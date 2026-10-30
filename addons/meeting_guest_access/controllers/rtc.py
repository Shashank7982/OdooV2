from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.discuss.rtc import RtcController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class SecureRtcController(RtcController):
    @http.route('/mail/rtc/channel/join_call', methods=['POST'], type='json', auth='public')
    @add_guest_to_context
    def channel_call_join(self, channel_id, check_rtc_session_ids=None, camera=False):
        channel = request.env['discuss.channel'].sudo().browse(int(channel_id)).exists()
        if channel and channel.meeting_id and not channel._meeting_is_joinable():
            raise NotFound()
        guest = request.env['mail.guest']._get_guest_from_context()
        if channel and channel.meeting_id and request.env.user._is_public() and guest and not channel._meeting_guest_can_join(guest):
            raise NotFound()
        return super().channel_call_join(channel_id, check_rtc_session_ids=check_rtc_session_ids, camera=camera)
