# Email Sending, Tracking & Cloudflare Tunnel — How It Actually Works

This documents findings from investigating three issues in this Odoo 18 instance:
1. Outgoing "From" address getting silently rewritten
2. A mass mailing showing `0 sent` then suddenly all sent
3. Link-click tracking showing clicks despite an expired Cloudflare tunnel

---

## 1. Why the "From" address doesn't always match what you typed

Odoo does **not** send mail with whatever From address you type. Each Outgoing Mail
Server (`ir.mail_server`) has a `from_filter` field. When Odoo picks a server to
send through, it walks servers by `sequence` and only uses a server if the
message's From address matches that server's `from_filter`. If no match is found,
it falls back to a server with no filter, or rewrites the From to something the
filter allows (e.g. `notifications_email`).

Relevant code: `odoo/addons/base/models/ir_mail_server.py`
- `_match_from_filter()` — matching logic
- `_get_default_from_filter()` / mail server selection (~line 800-880)

**Current servers configured in this DB** (`ir_mail_server`):

| name | smtp_host | sequence | from_filter |
|---|---|---|---|
| Brevo SMTP | smtp-relay.brevo.com | 2 | `admin@storeget.dpdns.org` |
| Gmail SMTP | smtp.gmail.com | 4 | (none) |
| Shaz Send | smtp.gmail.com | 4 | (none) |
| Mailpit (local) | localhost | 9 | (none) |
| Zoho SMTP | smtp.zoho.in | 10 | (none) |

**Fix if From gets rewritten unexpectedly:** add the sending address/domain to the
correct server's `from_filter` (Settings → Technical → Outgoing Mail Servers), and
make sure that address is verified/authenticated (SPF/DKIM) with that provider —
otherwise the provider itself may reject or flag it even if Odoo allows it.

**Note:** a specific mailing campaign can also hardcode `mailing_mailing.mail_server_id`,
which bypasses the `from_filter` matching entirely and forces that one server. This
was the cause of past failures going through Zoho instead of Brevo — campaign #76
had `mail_server_id` pinned to Zoho.

---

## 2. Why a mailing shows "0 sent" and then suddenly all sent

Mass mailings are **queued, not sent synchronously**. Clicking Send just creates
`mail.mail` records with `state = outgoing`. Actual delivery happens via scheduled
cron jobs:

| Cron | Interval |
|---|---|
| Mail Marketing: Process queue | every 1 minute |
| Mail: Email Queue Manager | every 5 minutes |

So a "0 sent, N in queue" snapshot just means you looked at it before the next
cron tick fired. A minute later the queue cron sends everything and the UI
reflects it. This is expected Odoo behavior (mass mailings are deliberately
throttled/queued rather than sent inline).

**Also expected:** once a `mail.mail` record sends successfully, Odoo auto-deletes
it (default `auto_delete = True`). Only failed/cancelled records remain in
`mail_mail` afterward — that's why a successful batch "disappears" from the table.

**Cancelled recipients are a data-quality issue, not a sending failure:**
- `mail_dup` — duplicate address already targeted in the same campaign
- `mail_email_invalid` — malformed email in the mailing list
- `mail_bl` — recipient is blacklisted (opted out / bounced previously)
- `mail_optout` — recipient opted out

Clean the mailing list (dedupe, validate format) to reduce cancellations on future sends.

---

## 3. What a "click" on a tracked link actually means

Odoo's click/open tracking uses **plain HTTP, not WebSockets**.

- Every link in a mass mailing is rewritten to a short redirect URL:
  `https://<web.base.url>/r/<code>/m/<mailing_id>`
- When clicked, the recipient's client sends an HTTP GET to that URL. The
  `link_tracker` controller on the Odoo server logs a row in
  `link_tracker_click` (with the requester's IP) and then 302-redirects to the
  real destination.
- Open-tracking works the same way via an embedded 1×1 tracking pixel image URL.

**This only works if the recipient's HTTP request can reach the server's public
URL at the moment they click** — not at send time, at click time. If the public
URL is dead when they click, the request just fails (DNS/timeout); nothing gets
logged.

**Key diagnostic: check the `ip` column on `link_tracker_click`.** A real
recipient shows their real public IP. A click from `127.0.0.1` means the request
originated from the Odoo server's own machine (local testing / preview / stale
`localhost` request) — not proof the public tunnel is reachable. In this
investigation, all recorded clicks were `127.0.0.1`, i.e. local, despite the
Cloudflare tunnel being dead.

```sql
select ltc.id, lt.url, ltc.create_date, ltc.ip
from link_tracker_click ltc
join link_tracker lt on lt.id = ltc.link_id
order by ltc.create_date desc
limit 10;
```

---

## 4. Cloudflare Quick Tunnel — why it "expires" and how to refresh it

This instance uses a Cloudflare **quick tunnel** (`cloudflared tunnel --url
http://localhost:8069`), which generates a random `*.trycloudflare.com`
hostname each run. Quick tunnels are meant for temporary testing:

- The URL is random every time `cloudflared` starts — it is **not stable**
  across restarts.
- The tunnel dies the instant the `cloudflared` process exits (crash, reboot,
  terminal closed, etc.) — nothing keeps it alive or auto-renews it.
- Odoo has no static IP of its own; it is only reachable from the internet
  while `cloudflared` is actively running and `web.base.url` points at the
  current tunnel hostname.

**Verify current state:**
```powershell
Get-Process | Where-Object { $_.ProcessName -like "*cloudflared*" }
Get-NetTCPConnection -LocalPort 8069
```
```sql
select key, value from ir_config_parameter
where key in ('web.base.url', 'web.base.url.freeze');
```

**To restore real external reachability:**
1. Start a new tunnel: `cloudflared tunnel --url http://localhost:8069`
2. Copy the newly generated `https://<random>.trycloudflare.com` URL.
3. Update Odoo: Settings → Technical → System Parameters → `web.base.url`
   (unfreeze `web.base.url.freeze` first if it's set to `True`, update the URL,
   then re-freeze if you want it locked).
4. Re-test a link/pixel and confirm the resulting `link_tracker_click.ip` is a
   real external IP, not `127.0.0.1`.

**For anything beyond ad-hoc testing:** use a **named Cloudflare Tunnel** tied to
your own domain (requires a Cloudflare account + DNS zone + a `cloudflared`
config file) instead of the quick/random tunnel — it gives you a stable
hostname that survives restarts.
