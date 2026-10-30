# Gmail Webhook Gateway

Push-based inbound Gmail processing (Gmail API `watch()` + Cloud Pub/Sub)
instead of IMAP polling. See `WEBHOOK_INBOUND_MAIL_README.md` at the repo
root for the full design rationale.

## Local/dev setup (using ngrok)

Google's Pub/Sub push subscription must POST to a public HTTPS URL — it
cannot reach `localhost`. For local development, tunnel your Odoo instance:

```
ngrok http 8069
```

Take the `https://xxxx.ngrok-free.app` URL ngrok gives you and set it as
`web.base.url` in Settings > Technical > System Parameters (or via
`ir.config_parameter`) **before** creating the webhook account, since the
account's Webhook URL field is computed from it.

Note: a free ngrok URL changes every time you restart the tunnel, so you'll
need to update `web.base.url` and re-point the Pub/Sub push subscription
(step 4 below) each time it changes. For anything beyond a quick test, use a
fixed domain (a paid ngrok domain, or your production host).

## One-time Google Cloud setup

1. Create a Google Cloud project (or reuse one).
2. Enable the **Gmail API** and **Cloud Pub/Sub API** for it.
3. Create a Pub/Sub **topic**, e.g. `gmail-inbound-notify`.
4. Create a **push subscription** on that topic, with push endpoint:
   `<your public URL>/gmail_webhook_gateway/webhook/<webhook_token>`
   (the exact value is shown on the `gmail.webhook.account` form after you
   save it once — `webhook_token` is generated automatically).
5. Grant Gmail's push service account publish rights on the topic:
   `gmail-api-push@system.gserviceaccount.com` → role `Pub/Sub Publisher`.
6. Create an **OAuth2 Client ID** (type: Web application) under
   "APIs & Services > Credentials". Add
   `<your public URL>/gmail_webhook_gateway/oauth/callback`
   as an authorized redirect URI. Note the Client ID and Client Secret.

## Odoo setup

1. Install this module.
2. Go to **Gmail Webhook > Accounts** and create a record:
   - Gmail Address: the mailbox to watch.
   - OAuth2 Client ID / Client Secret: from step 6 above.
   - GCP Project ID and Pub/Sub Topic: from steps 1–3 above.
   - Notify In Odoo UI: pick which users get a live toast notification when
     mail arrives.
3. Save, then click **Connect Gmail Account** and complete Google's consent
   screen as the mailbox owner.
4. Back in Odoo, click **Start Watching**.
5. Send yourself a test email at the watched address — it should appear in
   Odoo within seconds, with a toast notification for the configured users.

## Notes

- Gmail's `watch()` registration expires after at most 7 days; a daily cron
  (`Gmail Webhook Gateway: Renew Watch Registrations`) keeps it alive
  automatically.
- The webhook endpoint is verified by a random per-account `webhook_token`
  embedded in the URL, not by anything in the request body — keep the
  Webhook URL secret in the same way you'd keep an API key secret.
- This module deliberately does **not** remove `fetchmail.server`/IMAP
  polling for other mailboxes; it only replaces it for the specific mailbox
  configured here.
