# Email Open/Click Tracking — Why It Isn't Working & How To Fix It

## TL;DR

Your mailings show near-zero "Opened %" (e.g. 0.37%) despite 91% delivery
because `web.base.url` in your Odoo instance is set to `http://localhost:8069`.
Tracking pixels/links embedded in outgoing mail are built from this value,
so recipients' mail clients try to call back to `localhost` — which only
means "their own machine," not your server. The request goes nowhere, so
Odoo never learns the mail was opened.

This has **nothing to do** with which SMTP relay you send through (Gmail
SMTP, Brevo, etc.) — sending and tracking are two separate systems.

---

## 1. How email open/click tracking actually works (any tool, not just Odoo)

Email protocols (SMTP, IMAP, POP) have **no concept of "read receipts"**
that recipients' mailboxes report back to senders. Gmail, Outlook, Apple
Mail — none of them tell the sender "this was opened." There is no such
signal in the protocol.

Every marketing tool (Mailchimp, Brevo, Odoo's own `mass_mailing`, etc.)
uses the same workaround:

- **Open tracking**: embed a tiny invisible 1x1 image in the HTML email,
  hosted on the sender's (or ESP's) own server. When the recipient's mail
  client renders the email and loads external images, it fetches that
  image — that HTTP request *is* the "open" signal. No image request =
  no way to know it was opened.
- **Click tracking**: rewrite every link in the email to point at the
  sender's/ESP's server first (e.g. `/r/<code>/m/<trace_id>`), which logs
  the click, then 301-redirects to the real destination URL.

**Requirement in both cases**: the server hosting the pixel/redirect must
be reachable from the public internet, because the recipient could be
anywhere in the world.

### Where this lives in Odoo's code

- Pixel route: `addons/mass_mailing/controllers/main.py`
  - `GET /mail/track/<mail_id>/<token>/blank.gif` → calls
    `mailing.trace.set_opened()`
- Click route: same file
  - `GET /r/<code>/m/<mailing_trace_id>` → calls
    `link.tracker.click.add_click()`, then redirects
- Pixel URL construction: `addons/mass_mailing/models/mail_mail.py`
  (uses `web.base.url` + `_generate_mail_recipient_token`)
- Per-recipient results stored in `mailing.trace`:
  `email`, `res_id`, `open_datetime`, `links_click_datetime`, `trace_status`

---

## 2. Root cause found in this instance

```
web.base.url = http://localhost:8069
```

(checked via `ir_config_parameter` table, 2026-08-14)

Every tracking pixel/link Odoo embeds in outgoing mail is built from this
value. A recipient opening the email anywhere outside this machine cannot
reach `localhost:8069` — it resolves to *their own device*, not yours.

---

## 3. Why "Gmail/Yahoo block it" is only part of the picture

Even with a correct public `web.base.url`, expect imperfect (not zero)
tracking due to client-side behavior:

| Client | Behavior | Effect on your numbers |
|---|---|---|
| Gmail / Yahoo | Proxies remote images through their own servers (`googleusercontent.com`), sometimes caching so a real open doesn't always re-fetch | Noisy, may undercount slightly, but does NOT explain near-0% |
| Outlook / many corporate clients | Remote images blocked by default until user clicks "Download pictures" | True false-negative — real open not counted |
| Apple Mail (Mail Privacy Protection) | Prefetches all images for all incoming mail on Apple's servers regardless of whether user opens | Inflates opens toward 100% for Apple Mail users, even unopened mail |

None of these explain a **0.37% open rate on 91% delivered mail** — that
pattern means the pixel URL isn't resolving at all (our root cause above),
not client-side blocking.

---

## 4. Two ways to actually get tracking working

Both require your Odoo instance (or someone's server) to have a public,
internet-reachable address. There's no way around this — it's structural
to how the tracking pixel/webhook technique works.

### Option A — Odoo's built-in pixel/click tracking (already built)

1. Get Odoo reachable at a public URL:
   - **Quick/testing**: tunnel tool like `ngrok http 8069` → gives a
     temporary public URL (changes on restart unless paid tier).
   - **Production**: deploy on a VPS/cloud server with a real domain and
     HTTPS.
2. Update the system parameter:
   ```
   Settings → Technical → System Parameters → web.base.url
   ```
   Set it to the public URL (e.g. `https://mail.yourdomain.com` or the
   ngrok URL).
3. Send a test mailing, open it from a device outside your local network.
4. Check Email Marketing → the mailing → recipient traces should show
   `Opened`.

No code changes needed — this is 100% existing, working Odoo
functionality (`mass_mailing` module), just blocked by network config.

### Option B — Brevo's own tracking + webhook back to Odoo

Only relevant if sending via **Brevo** (Gmail SMTP has no tracking/webhook
capability at all — it's a raw relay).

1. Enable open/click tracking in your Brevo account/API settings. Brevo
   rewrites the pixel/links to point at Brevo's own (always-public)
   servers — no reachability issue on that side.
2. Configure a Brevo **webhook** pointing at an endpoint on your Odoo
   instance (e.g. a custom controller route) for `opened` / `clicked`
   events.
3. **Important**: this does NOT remove the "needs to be public" problem —
   it just moves it. Brevo's servers now need to reach *your* webhook
   endpoint, which still requires Odoo to be publicly reachable (same
   tunnel/VPS requirement as Option A).
4. Requires custom development: a controller to receive Brevo's webhook
   payload and map it (via Brevo's message-id) to the corresponding
   `mailing.trace` record, then call `set_opened()` / click equivalent.

**Trade-off**: more reliable long-term (Brevo's tracking infra handles
Gmail proxy/Apple MPP edge cases better than a DIY pixel), but requires
custom webhook development work versus Option A which is zero-dev,
config-only.

---

## 5. Recommendation

Given no public server/domain exists yet:

1. Set up a tunnel (ngrok) now to unblock testing immediately with
   **zero new code** (Option A) — update `web.base.url`, done.
2. When ready for real production use, move to a proper VPS + domain, and
   optionally revisit Option B (Brevo webhook) if Odoo's own pixel proves
   unreliable enough to justify the extra development.
