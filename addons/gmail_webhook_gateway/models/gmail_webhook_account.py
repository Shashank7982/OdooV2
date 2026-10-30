# -*- coding: utf-8 -*-
import base64
import json
import logging
import uuid
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1/users/me'
# gmail.readonly is enough to read messages; gmail.metadata would be lighter
# but doesn't allow fetching the raw RFC822 body we need for message_process.
OAUTH_SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
# Gmail's watch() registration is only valid for a maximum of 7 days.
WATCH_MAX_LIFETIME_DAYS = 7
WATCH_RENEW_MARGIN_HOURS = 24


class GmailWebhookAccount(models.Model):
    """One watched Gmail mailbox: OAuth2 credentials + Pub/Sub watch state.

    Replaces IMAP polling for this mailbox with push notifications: Gmail API
    `watch()` registers interest in mailbox changes, Google Cloud Pub/Sub
    delivers a lightweight change notification to our webhook controller,
    and this model fetches + hands off the actual new message(s) to Odoo's
    standard `mail.thread.message_process()` - the same entry point
    `fetchmail.server` (IMAP) uses, so downstream routing/classification is
    reused unchanged.
    """
    _name = 'gmail.webhook.account'
    _description = 'Gmail Webhook Account'
    _inherit = ['mail.thread']
    _rec_name = 'email'

    active = fields.Boolean(default=True)
    email = fields.Char(string='Gmail Address', required=True, tracking=True,
                         help="The @gmail.com mailbox to watch. Outgoing mail should be "
                              "sent from this same address for reply-threading to work.")

    # --- OAuth2 app credentials (from Google Cloud Console) ---
    client_id = fields.Char(string='OAuth2 Client ID', required=True)
    client_secret = fields.Char(string='OAuth2 Client Secret', required=True, groups='base.group_system')

    # --- OAuth2 mailbox tokens (obtained via the consent flow) ---
    refresh_token = fields.Char(string='Refresh Token', groups='base.group_system', copy=False)
    access_token = fields.Char(string='Access Token', groups='base.group_system', copy=False)
    token_expiry = fields.Datetime(string='Access Token Expiry', copy=False)

    # --- Pub/Sub ---
    gcp_project_id = fields.Char(string='GCP Project ID', required=True,
                                  help="The Google Cloud project that owns the Pub/Sub topic.")
    pubsub_topic_name = fields.Char(string='Pub/Sub Topic', required=True, default='gmail-inbound-notify',
                                     help="Short topic name (not the full path), e.g. 'gmail-inbound-notify'. "
                                          "Must already exist in the GCP project with a push subscription "
                                          "pointing at this record's Webhook URL below.")
    webhook_token = fields.Char(string='Webhook Secret Token', copy=False, readonly=True,
                                 default=lambda self: uuid.uuid4().hex,
                                 help="Random token embedded in the webhook URL so only Pub/Sub push requests "
                                      "that know it are accepted.")
    webhook_url = fields.Char(string='Webhook URL', compute='_compute_webhook_url')

    # --- Watch / history state ---
    last_history_id = fields.Char(string='Last History Id', copy=False,
                                   help="Gmail mailbox history checkpoint; new messages are diffed from here.")
    watch_expiration = fields.Datetime(string='Watch Expires On', copy=False)

    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('authorized', 'Connected (Not Watching)'),
        ('watching', 'Watching'),
        ('error', 'Error'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    error_message = fields.Text(string='Last Error', copy=False)

    notify_user_ids = fields.Many2many('res.users', string='Notify In Odoo UI',
                                        help="These users get an in-app toast notification whenever a new "
                                             "message is fetched through this webhook. Leave empty to skip.")

    _sql_constraints = [
        ('webhook_token_unique', 'unique(webhook_token)', 'Webhook token must be unique.'),
    ]

    def _compute_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for account in self:
            account.webhook_url = f'{base_url}/gmail_webhook_gateway/webhook/{account.webhook_token}'

    # ------------------------------------------------------------
    # OAuth2 consent flow
    # ------------------------------------------------------------

    def _oauth_redirect_uri(self):
        # Google only allows registering http://localhost as an OAuth redirect
        # URI without domain-ownership verification - which lets this work even
        # when web.base.url points at a free tunnel domain (trycloudflare.com,
        # ngrok-free.app, ...) that Google's redirect URI validator rejects
        # outright. The OAuth callback only needs to reach the user's own
        # browser, unlike the Pub/Sub webhook below, which needs the public
        # tunnel URL since Google's servers POST to it directly.
        ICP = self.env['ir.config_parameter'].sudo()
        base_url = ICP.get_param('gmail_webhook_gateway.oauth_base_url') or ICP.get_param('web.base.url') or ''
        return f'{base_url}/gmail_webhook_gateway/oauth/callback'

    def action_connect_gmail_account(self):
        """Open Google's OAuth2 consent screen. On success, Google redirects
        back to our callback controller with a one-time authorization code."""
        self.ensure_one()
        if not self.client_id or not self.client_secret:
            raise UserError(_('Set the OAuth2 Client ID and Client Secret first.'))
        params = {
            'client_id': self.client_id,
            'redirect_uri': self._oauth_redirect_uri(),
            'response_type': 'code',
            'scope': OAUTH_SCOPES,
            'access_type': 'offline',   # required to get a refresh_token
            'prompt': 'consent',        # force refresh_token on repeat authorizations too
            'state': str(self.id),
        }
        url = GOOGLE_AUTH_URL + '?' + '&'.join(f'{k}={requests.utils.quote(str(v))}' for k, v in params.items())
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def _oauth_exchange_code(self, code):
        """Exchange a one-time authorization code for access/refresh tokens.
        Called by the OAuth callback controller."""
        self.ensure_one()
        try:
            resp = requests.post(GOOGLE_TOKEN_URL, data={
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self._oauth_redirect_uri(),
                'grant_type': 'authorization_code',
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            self.write({'state': 'error', 'error_message': str(exc)})
            raise UserError(_('Google rejected the authorization: %s', exc)) from exc

        vals = {
            'access_token': data['access_token'],
            'token_expiry': fields.Datetime.now() + timedelta(seconds=data.get('expires_in', 3600)),
            'state': 'authorized',
            'error_message': False,
        }
        if data.get('refresh_token'):
            vals['refresh_token'] = data['refresh_token']
        elif not self.refresh_token:
            # No refresh_token returned and we don't already have one: the user
            # likely authorized before without `prompt=consent`. They must
            # revoke access at https://myaccount.google.com/permissions and retry.
            raise UserError(_(
                'Google did not return a refresh token. Revoke this app\'s access at '
                'https://myaccount.google.com/permissions and click "Connect Gmail Account" again.'))
        self.write(vals)

    def _ensure_access_token(self):
        """Return a valid access token, refreshing it first if it's expired
        or about to expire."""
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_('This account is not connected yet: click "Connect Gmail Account" first.'))
        if self.access_token and self.token_expiry and self.token_expiry > fields.Datetime.now() + timedelta(minutes=2):
            return self.access_token
        try:
            resp = requests.post(GOOGLE_TOKEN_URL, data={
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            self.write({'state': 'error', 'error_message': f'Token refresh failed: {exc}'})
            raise UserError(_('Failed to refresh the Gmail access token: %s', exc)) from exc
        self.write({
            'access_token': data['access_token'],
            'token_expiry': fields.Datetime.now() + timedelta(seconds=data.get('expires_in', 3600)),
        })
        return self.access_token

    def _gmail_api_headers(self):
        return {'Authorization': f'Bearer {self._ensure_access_token()}'}

    # ------------------------------------------------------------
    # watch() registration / renewal
    # ------------------------------------------------------------

    def action_start_watching(self):
        for account in self:
            account._register_watch()
        return True

    def _register_watch(self):
        """Tell Gmail to publish mailbox-change notifications to our Pub/Sub
        topic. Must be re-called at least every 7 days (see the renewal cron)."""
        self.ensure_one()
        topic = f'projects/{self.gcp_project_id}/topics/{self.pubsub_topic_name}'
        try:
            resp = requests.post(
                f'{GMAIL_API_BASE}/watch',
                headers=self._gmail_api_headers(),
                json={'topicName': topic, 'labelIds': ['INBOX']},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            self.write({'state': 'error', 'error_message': f'watch() failed: {exc}'})
            raise UserError(_('Failed to register the Gmail watch: %s', exc)) from exc

        expiration_ms = int(data['expiration'])  # epoch millis, Google-side max = now + 7 days
        self.write({
            'state': 'watching',
            'last_history_id': str(data['historyId']),
            'watch_expiration': fields.Datetime.now() + timedelta(
                seconds=min(expiration_ms / 1000 - fields.Datetime.now().timestamp(), WATCH_MAX_LIFETIME_DAYS * 86400)),
            'error_message': False,
        })

    @api.model
    def _cron_renew_watch(self):
        """Renew any watch registration expiring within the next 24h. This
        cron does no mail-fetching itself - it only keeps push notifications
        alive, since Gmail silently stops sending them once a watch expires."""
        deadline = fields.Datetime.now() + timedelta(hours=WATCH_RENEW_MARGIN_HOURS)
        accounts = self.search([
            ('state', '=', 'watching'),
            ('watch_expiration', '<=', deadline),
        ])
        for account in accounts:
            try:
                account._register_watch()
            except Exception:  # noqa: BLE001 - never let one bad account break the cron
                _logger.exception('Failed to renew Gmail watch for %s', account.email)

    # ------------------------------------------------------------
    # Pub/Sub push handling
    # ------------------------------------------------------------

    def _process_pubsub_push(self, envelope):
        """Entry point called by the webhook controller with the decoded
        Pub/Sub push body. `envelope` is the JSON dict Google POSTs, of the
        shape {"message": {"data": "<base64>", "messageId": ..., ...}, "subscription": ...}."""
        self.ensure_one()
        message = envelope.get('message') or {}
        data_b64 = message.get('data')
        if not data_b64:
            _logger.warning('Gmail webhook push for %s had no data payload, ignoring', self.email)
            return
        try:
            notification = json.loads(base64.b64decode(data_b64).decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as exc:
            _logger.warning('Gmail webhook push for %s had an undecodable payload: %s', self.email, exc)
            return

        new_history_id = str(notification.get('historyId') or '')
        if not new_history_id:
            return
        self._fetch_new_messages(new_history_id)

    def _fetch_new_messages(self, new_history_id):
        """Diff the mailbox history since our last known checkpoint, fetch
        every newly-added message's raw content, and hand each one to
        `mail.thread.message_process()` - the same entry point IMAP fetching
        uses, so all existing routing/classification is reused unchanged."""
        self.ensure_one()
        if not self.last_history_id:
            # First push since a fresh watch(): nothing to diff against yet,
            # just move the checkpoint forward.
            self.last_history_id = new_history_id
            return

        message_ids = []
        page_token = None
        try:
            while True:
                params = {'startHistoryId': self.last_history_id, 'historyTypes': 'messageAdded'}
                if page_token:
                    params['pageToken'] = page_token
                resp = requests.get(f'{GMAIL_API_BASE}/history', headers=self._gmail_api_headers(),
                                     params=params, timeout=15)
                if resp.status_code == 404:
                    # startHistoryId too old (Gmail only retains ~1 week of history):
                    # we may have missed messages. Resync the checkpoint and stop;
                    # the fallback/manual sync can be used to catch up if needed.
                    _logger.warning('Gmail history checkpoint expired for %s, resyncing to %s',
                                     self.email, new_history_id)
                    self.last_history_id = new_history_id
                    return
                resp.raise_for_status()
                payload = resp.json()
                for record in payload.get('history', []):
                    for added in record.get('messagesAdded', []):
                        message_ids.append(added['message']['id'])
                page_token = payload.get('nextPageToken')
                if not page_token:
                    break
        except requests.RequestException as exc:
            self.write({'state': 'error', 'error_message': f'history.list failed: {exc}'})
            _logger.exception('Failed to list Gmail history for %s', self.email)
            return

        for message_id in message_ids:
            self._fetch_and_process_message(message_id)

        self.last_history_id = new_history_id
        if self.state == 'error':
            self.write({'state': 'watching', 'error_message': False})

    def _fetch_and_process_message(self, message_id):
        self.ensure_one()
        try:
            resp = requests.get(f'{GMAIL_API_BASE}/messages/{message_id}', headers=self._gmail_api_headers(),
                                 params={'format': 'raw'}, timeout=15)
            resp.raise_for_status()
            raw_b64url = resp.json()['raw']
        except requests.RequestException as exc:
            _logger.exception('Failed to fetch Gmail message %s for %s: %s', message_id, self.email, exc)
            return

        raw_bytes = base64.urlsafe_b64decode(raw_b64url + '=' * (-len(raw_b64url) % 4))
        try:
            thread = self.env['mail.thread'].sudo().message_process(None, raw_bytes)
        except Exception:  # noqa: BLE001 - one bad message must not break the push handler
            _logger.exception('message_process() failed for Gmail message %s (%s)', message_id, self.email)
            return

        self._notify_ui(message_id, thread)

    def _notify_ui(self, gmail_message_id, thread_record):
        """Toast a live in-app notification to the configured users, on top
        of Odoo's existing automatic chatter/bus updates for the created
        `mail.message` itself."""
        self.ensure_one()
        if not self.notify_user_ids:
            return
        partners = self.notify_user_ids.mapped('partner_id')
        for partner in partners:
            partner._bus_send('simple_notification', {
                'type': 'info',
                'title': _('New email received'),
                'message': _('New message on %s (Gmail webhook)', self.email),
                'sticky': False,
            })
