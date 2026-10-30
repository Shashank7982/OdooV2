# Cloudflare Tunnel & Email Testing Setup

## Cloudflare Permanent Named Tunnel (Active: hireverse.dpdns.org -> :3000)

`cloudflared` is installed at `C:\Program Files (x86)\cloudflared\cloudflared.exe`.

### Active Permanent Named Tunnel: `odoo18`
- **Tunnel Name:** `odoo18`
- **Tunnel ID:** `d02ba936-603f-4cb8-a3c3-0768f107b051`
- **Public Domain:** `https://hireverse.dpdns.org`
- **Local Service:** `http://localhost:3000` (Odoo 18 XML-RPC / Web port)
- **Config File:** `C:\Users\shash\.cloudflared\config.yml`
- **Log File:** `C:\Users\shash\.cloudflared\tunnel.log`

### Auto-Start on System Boot / User Logon
The tunnel is permanently installed into the Windows User Startup folder:
- **Startup script:** `C:\Users\shash\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\CloudflareTunnel-Odoo18.vbs`
- Runs silently in the background via `wscript.exe` with no visible console window.

### Management & Diagnostics Scripts (in workspace root)
- **Status check:** `powershell -ExecutionPolicy Bypass -File .\check_cloudflare_tunnel.ps1`
- **Start tunnel:** `.\start_cloudflare_tunnel.bat`
- **Stop tunnel:** `.\stop_cloudflare_tunnel.bat`

### Odoo System Parameters
- `web.base.url`: `https://hireverse.dpdns.org`
- `web.base.url.freeze`: `True`

## Email deliverability note: `storeget.dpdns.org` is Spamhaus-blocklisted

Mail sent from `admin@storeget.dpdns.org` (via Zoho Mail) bounces from
Outlook/Microsoft recipients with `550 5.7.1 ... MailFrom domain is listed in
Spamhaus`. Confirmed via Spamhaus DBL lookup that the listing is on the
**parent domain `dpdns.org`** (a free public dynamic-DNS/subdomain service),
not specifically on `storeget`. This is essentially unfixable by delisting —
free shared subdomain providers get relisted from abuse by other users of the
same domain. Real fix: send from a domain you actually own/register.

## Gmail Webhook Gateway test account

DB `odoo18db`, `gmail_webhook_account` id 1:
- email: `mohit.kapoormk19@gmail.com`
- gcp_project_id: `regal-fortress-505720`
- pubsub_topic_name: `gmail-inbound-notify`
- webhook_token: `6ab7ba82d01249cd8b61776d1dcb5c97`
- Webhook endpoint (Pub/Sub push URL):
  `https://hoping-synthesis-stylish-interactions.trycloudflare.com/gmail_webhook_gateway/webhook/6ab7ba82d01249cd8b61776d1dcb5c97`

A second account (`agentsub7982@gmail.com`, GCP project `regal-fortress-505720-c0`
a.k.a. "My Project 76145") was also being set up; ran into a
`redirect_uri_mismatch` during Google's OAuth consent — the fix was re-saving
the exact Authorized redirect URI in Google Cloud Console and waiting for
Google's propagation delay (their own UI warns "five minutes to a few hours").

## Disposable test recipient addresses

For testing Odoo mass-mailing / mailing lists without sending to real people.
These are throwaway inboxes on free temp-mail services — **not for production
use**, and not a fix for the deliverability problem above (that requires a
real, owned sending domain).

### Tigrmail (`api.tigrmail.com`)

Account created at console.tigrmail.com. API token (keep secret):

```
cpa98r4xz21o8dqufmkj4od0uf8uveufw29un9knnevrrnjwwfi01ao8ymw9xpck
```

Create an inbox: `POST https://api.tigrmail.com/v1/inboxes` with header
`Authorization: Bearer <token>`.

Check for a received message: `GET https://api.tigrmail.com/v1/messages?inbox=<address>`
(blocks up to 3 minutes waiting, auto-marks message as read).

10 inboxes created so far:

```
covert-purr-yfk9xxfmj0pbibp231@den.tigrmail.com
agile-mongoo-y06y2wsfz6wcvedabg@den.tigrmail.com
wild-korat-zb7a25fobx73ccjbmu@den.tigrmail.com
valor-chartr-sar2s9ol6l9ttj8ahw@den.tigrmail.com
bendy-colony-7xx2s17dwnqw8ir8sk@den.tigrmail.com
purry-luna-oi0jgnogurcgk22p3f@den.tigrmail.com
brave-siames-xc4mmsof3uvf8iaxsq@den.tigrmail.com
loving-muzzle-q0agmpe3snqp3835cp@den.tigrmail.com
dark-meow-uw8i6un5wqf7zu8prc@den.tigrmail.com
big-peter-tz8rbt30k84pbogq46@den.tigrmail.com
```

### mail.tm (`api.mail.tm`)

Fully public API, no signup required — accounts created directly via
`POST https://api.mail.tm/accounts` with `{"address": ..., "password": ...}`.
Unlike Tigrmail, reading messages requires the account password: get a bearer
token via `POST https://api.mail.tm/token` with the same address/password,
then `GET https://api.mail.tm/messages`.

Domain used: `emalupe.com` (mail.tm's currently active public domain — check
`GET https://api.mail.tm/domains` since this rotates).

| Email | Password |
|---|---|
| odootest22789001@emalupe.com | TigrOdoo!440001 |
| odootest49716002@emalupe.com | TigrOdoo!224002 |
| odootest51418003@emalupe.com | TigrOdoo!809003 |
| odootest68480004@emalupe.com | TigrOdoo!731004 |
| odootest75313005@emalupe.com | TigrOdoo!850005 |
| odootest74314009@emalupe.com | TigrOdoo!284009 |
| odootest904690010@emalupe.com | TigrOdoo!1270010 |
| odootest343680011@emalupe.com | TigrOdoo!7460011 |
| odootest663270014@emalupe.com | TigrOdoo!3840014 |
| odootest398490015@emalupe.com | TigrOdoo!5960015 |
