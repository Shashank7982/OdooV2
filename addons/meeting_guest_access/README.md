# Discuss meeting dial-in

This module adds secure guest admission to Odoo Discuss video meetings and an optional PSTN dial-in flow.

## Important architecture

Odoo Discuss uses browser WebRTC/RTC sessions. A telephone caller cannot join that media session directly. The dial-in implementation therefore uses a voice provider with TwiML-compatible webhooks (for example Twilio) and places phone callers into a provider conference keyed to the Odoo meeting. Browser participants continue to use the native Discuss RTC call. To mix phone audio into the native browser RTC media, deploy a separate SIP/WebRTC media bridge; this module does not pretend the two media planes are automatically mixed.

## Setup

1. Install or upgrade `meeting_guest_access`.
2. Obtain a voice-capable number from a provider. An SMS-only number cannot receive calls.
3. In Settings, enable **Meeting dial-in**, select the TwiML-compatible provider, and enter the number.
4. Configure the provider's incoming-call webhook to `https://YOUR_ODOO_HOST/meeting/dialin/voice`.
5. Start a Discuss video meeting. The invitation panel displays the dial-in number and a meeting-specific six-digit PIN.
6. Call the number and enter the PIN. The caller is placed into the provider conference for that meeting.

## Security

- Do not use shared or SMS-only numbers for voice dial-in.
- Keep provider credentials out of source control and restrict access to Odoo administrators.
- Use HTTPS for the webhook endpoint.
- Rotate the provider token if it is exposed.
- Keep the meeting closed until the host is ready to admit participants.
