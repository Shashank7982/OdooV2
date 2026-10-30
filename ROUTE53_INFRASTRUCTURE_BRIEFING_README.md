# Infrastructure Briefing: Domain, DNS, Mail Routing & Deployment — What We're Doing and Where Route 53 Fits

**Audience:** Muthumaniraj (AWS/cloud-emulator background), to evaluate whether/how
Route 53 (or an emulator of it) covers our needs — DNS, mail routing, webhooks,
mail traffic management, and the upcoming production website + payment gateway
deployment.

**Author context:** This is a working Odoo 18 instance. Everything below reflects
what is actually built/configured today, not a hypothetical architecture — see the
individual README files in the repo root for full investigation detail on each
topic; this document is the consolidated briefing.

---

## 1. What we're building, in one paragraph

An Odoo-based business system (CRM, sales, invoicing, email marketing, SMS,
snail-mail letters, and a website with e-commerce) that needs to: (a) send and
receive email reliably under our own domain instead of a personal Gmail account,
(b) receive real-time inbound events from external services (Gmail, payment
providers) via webhooks, (c) run scheduled background jobs (mail queues, payment
follow-ups) without them starving each other, and (d) soon be deployed as a public
production website with a **payment gateway (Stripe)** and an **affiliate/referral
sales feature**, replacing the current local-machine + Cloudflare-tunnel setup.

Route 53 (AWS's DNS + domain registration service) is one candidate for the piece
that ties a real domain name to all of this. The rest of this doc explains every
concept Muthumaniraj needs to evaluate it against, plus what's already working, so
he can check specifically: **does Route 53 (or the emulator) support everything
below, and does it fit the free/low-cost constraint we've been operating under?**

---

## 2. Core concepts (for shared vocabulary)

### Domain & nameservers
A **domain** (e.g. `yourdomain.com`) is just a name registered with a registrar.
By itself it does nothing — it needs **nameservers**, which are the servers that
answer "where do I find things under this domain" for the rest of the internet.
Whoever controls the nameservers controls DNS for that domain, **regardless of who
you registered the domain with**. You can register a domain at one place (e.g.
DigitalPlat, deSEC-based free domains) and point its nameservers at a completely
different DNS host (e.g. Cloudflare, Route 53) — that's called **delegation**.

We hit this directly: our current test domain `storeget.dpdns.org` is registered
under deSEC's free dynamic-DNS service, with deSEC as the authoritative
nameserver. We wanted Cloudflare to manage DNS for a subdomain of it (for a stable
tunnel hostname) and **couldn't**, because deSEC never delegated that subdomain to
Cloudflare's nameservers — a CNAME to Cloudflare's tunnel endpoint doesn't work
unless Cloudflare is authoritative for the zone. This is the exact kind of
question to ask about Route 53: if we eventually buy a real domain, can Route 53
be made the authoritative nameserver for it cleanly, and can subdomains be
delegated in/out cleanly if needed later?

### DNS record types we actually use
| Record | Purpose | Where we've used it |
|---|---|---|
| A / CNAME | Points a hostname at an IP or another hostname | Would point the production website at our server/load balancer |
| MX | Says which mail servers receive mail for the domain | Currently → Zoho's MX servers (`mx.zoho.in` etc.) |
| TXT (SPF) | Lists which servers are allowed to *send* mail as this domain | `v=spf1 include:zoho.in ~all` |
| TXT (DKIM) | Publishes the public key used to verify signed outgoing mail | `zmail._domainkey` → Zoho's key |
| TXT (DMARC) | Policy for what to do when SPF/DKIM fail | `_dmarc` → currently misconfigured, needs fixing |
| TXT (verification) | Proves domain ownership to a third-party service | Used for both Zoho and Brevo verification |
| NS | Delegates a subdomain to a different nameserver | Attempted (blocked) for Cloudflare tunnel subdomain |

### Email routing & mail server protocols
- **SMTP** — protocol for *sending* mail (Odoo → outbound relay → recipient's server).
- **IMAP** — protocol for *reading/syncing* a mailbox (used for polling inbound replies).
- **POP3** — older, simpler inbound protocol (not used here).
- Today: Odoo sends via **Zoho SMTP** (`smtp.zoho.in:465`, SSL/TLS) and previously
  via Gmail SMTP and Brevo SMTP relay (all three have been configured/tested at
  different points — see `ZOHO_MAIL_SETUP_README.md` and `EMAIL_DOMAIN_MIGRATION_README.md`).
- Inbound mail is currently fetched by IMAP polling (`fetchmail.server`, a cron
  every 5–15 min) — see "Webhooks" below for why we're moving off this.

### Security: SPF / DKIM / DMARC (mail server security, briefly)
These three DNS-published records are how a receiving mail server (Gmail, Outlook,
Yahoo) decides whether to trust a message claiming to be "from" our domain:
- **SPF** — whitelist of IPs/servers allowed to send as us.
- **DKIM** — cryptographic signature proving the message wasn't altered and really
  came from a server we authorized.
- **DMARC** — the enforcement policy (ignore / quarantine / reject) when SPF/DKIM
  fail, plus where to send reports about failures (`rua=mailto:...`).

All three must be correctly set for **whatever domain/subdomain we send from** —
this is domain-specific, not account-specific. Whoever hosts our DNS (Route 53 or
otherwise) needs to support arbitrary TXT records so we can publish these for
each provider (Zoho for mailbox, potentially Brevo/SES for marketing volume).

### Webhooks
A **webhook** is a receiving service saying "call this URL the instant something
happens" instead of us polling on a timer. We use/plan two:
1. **Gmail inbound mail** — via Gmail API `watch()` + Google Cloud Pub/Sub push
   (Gmail has no classic webhook; this is its push-notification equivalent). Needs
   Odoo reachable at a **public HTTPS URL** — see `WEBHOOK_INBOUND_MAIL_README.md`
   for the full mechanism and why polling isn't good enough for time-sensitive
   replies (support/order mail waiting behind bounce/marketing mail in the same queue).
2. **Payment gateway (Stripe)** — Stripe pushes payment/webhook events (payment
   succeeded, failed, disputed) to a URL we register with them. Same requirement:
   Odoo must have a stable public HTTPS address.

**Key implication for Route 53 evaluation:** webhooks don't care about DNS
directly, but they need a **stable, always-reachable public endpoint** — which
means DNS (pointing a hostname at our server) plus TLS plus the server actually
being up matters a lot here. A quick Cloudflare tunnel URL that changes on every
restart (our current stopgap — see `CLOUDFLARE_TUNNEL_AND_EMAIL_TESTING_README.md`)
is not viable long-term for this exact reason: every restart would mean
re-registering the webhook URL with Google/Stripe.

### Load balancing (mail traffic management)
Important distinction we already had to work through internally: a **load
balancer** spreads incoming **web/HTTP traffic** across multiple server instances.
It does **not** parallelize background/cron jobs — Odoo already prevents a cron
job from double-running via a DB lock, so more servers behind a load balancer
doesn't give more mail-sending throughput. Our actual mail-traffic bottleneck was
Odoo's own `max_cron_threads` (default 2, shared by all scheduled jobs) and
`db_maxconn`/Postgres `max_connections`. Full breakdown in
`CRON_AND_EMAIL_DELIVERABILITY_README.md`. When asking Muthumaniraj to check
Route 53 for "load balancing," the real ask is: **does AWS's ecosystem (Route 53
health checks + ELB, if we go that route) help distribute *web* traffic once we
have multiple app servers**, not mail-sending concurrency — that's an Odoo-config
problem, separate from DNS.

### DNS reputation / IP reputation / Spamhaus
Domains and IPs both carry a **reputation** with mail providers, independent of
whether SPF/DKIM/DMARC are technically correct. We hit this directly:
`storeget.dpdns.org` mail bounced from Outlook with `550 ... listed in Spamhaus`
— **not** because of misconfiguration, but because the *parent* domain
(`dpdns.org`, a free public dynamic-DNS provider) was blocklisted due to abuse by
other users of the same shared domain. This is unfixable short of switching to a
domain we actually own outright. Separately, a brand-new domain/IP has **zero
reputation** and needs a "warm-up" period of consistent, low-volume, non-spammy
sending before big mailbox providers (Gmail, Outlook, Yahoo) trust it — this is
true no matter which DNS/cloud provider we use. Route 53 itself has no bearing on
domain/IP reputation; that's determined by the registrar/domain choice and sending
behavior, not the DNS host. Worth telling Muthumaniraj explicitly so he doesn't
go looking for a "reputation setting" in Route 53 — it doesn't exist there.

### IPv4 vs IPv6
Relevant mainly for: (a) A/AAAA records when pointing our domain at a server —
AAAA is the IPv6 equivalent of an A record, and (b) some mail/security checks
(reverse DNS / PTR records) being IPv4-only in older tooling. Ask him to check
whether Route 53 (or whichever cloud host we deploy to) supports both, and
whether reverse-DNS (PTR) setup is available for our sending IP — PTR records
matter for mail deliverability (a mismatched or missing PTR is another spam-filter
signal, separate from SPF/DKIM/DMARC).

---

## 3. What's actually running today (current state, honestly)

- **Odoo runs locally** on a personal machine, exposed to the internet via a
  **Cloudflare quick tunnel** (`cloudflared tunnel --url http://localhost:8069`),
  which generates a **random `trycloudflare.com` URL that changes every restart**.
  This is a testing stopgap, not production infrastructure.
- **Mail domain:** `storeget.dpdns.org` — a free subdomain from a dynamic-DNS
  provider (deSEC), **not a domain we own**. It is Spamhaus-blocklisted at the
  parent-domain level (unfixable) and has zero sending reputation as a brand-new
  domain besides.
- **Outgoing mail:** Zoho SMTP (`smtp.zoho.in`), with Gmail SMTP and Brevo SMTP
  also configured as alternate servers.
- **Inbound mail:** IMAP polling today; Gmail API + Pub/Sub push webhook designed
  but not fully cut over (see `WEBHOOK_INBOUND_MAIL_README.md` migration phases).
- **Custom addons already built:** `gmail_webhook_gateway` (Pub/Sub push
  receiver), `marketing_mail_gateway` (inbound classification: bounce/unsubscribe/
  reply/order/support), `mail_inbox_classifier`, `sale_snailmail` (physical letter
  sending via Odoo's `snailmail` module), `sms_twilio` (SMS via Twilio).
- **Known incident:** a mass mailing to 178 recipients stalled twice — once from a
  misconfigured cron interval (1/day instead of 1/minute), once from the
  Spamhaus-blocklisted domain triggering Zoho's own abuse throttling after ~52
  sends. Full timeline in `MASS_MAILING_INCIDENT_LOG.md`. This is the clearest
  concrete illustration of why "own domain + real DNS host + correct mail auth"
  isn't optional — it already broke production-like usage once.
- **Email open/click tracking is broken** for an unrelated but related reason:
  `web.base.url` is set to `http://localhost:8069`, so tracking pixels/links
  embedded in outgoing mail point at a URL no external recipient can ever reach.
  This will auto-resolve once we're on a real public domain (see
  `EMAIL_OPEN_CLICK_TRACKING_README.md`).

**None of this is production-grade yet.** The local machine + tunnel + free
shared subdomain setup was for development/testing. The end goal (below) replaces
all of it.

---

## 4. Where we're going next (the assignment's actual scope)

Going forward we are deploying:
1. **A public production website** (Odoo website + e-commerce), replacing the
   local machine + Cloudflare tunnel setup with real hosting.
2. **A payment gateway** — `payment_stripe_custom` addon is already scaffolded
   (Stripe integration, webhook controller for payment events).
3. **An affiliate/referral sales feature** — `website_sale_affiliate` addon
   already scaffolded.
4. **Everything from section 3 above, done properly**: an owned domain (not a free
   dynamic-DNS subdomain), correct SPF/DKIM/DMARC for that domain, a real inbound
   webhook path (Gmail push and/or a dedicated transactional provider), stable
   public HTTPS so tracking/webhooks work, and cron/thread/connection limits sized
   for real traffic instead of default local-dev settings.

## 5. What we need Muthumaniraj to check on Route 53 / cloud emulators

Please check whether Route 53 (or whichever AWS emulator he has access to) covers:

1. **Domain registration and/or hosted zones** — can it be the authoritative
   nameserver for a domain we register (through Route 53 itself, or a domain
   registered elsewhere and delegated in)?
2. **All the record types in section 2's table** — A/AAAA, CNAME, MX, TXT (SPF/
   DKIM/DMARC/verification), NS for subdomain delegation.
3. **Health checks + routing policies** — Route 53 supports failover/latency-based
   routing; relevant once we have more than one app server or want DNS-level
   failover for the production site.
4. **Integration with a load balancer** (AWS ALB/ELB) for the production website's
   HTTP traffic — separately from mail, per the load-balancing note above.
5. **Reverse DNS / PTR record support** for whatever IP ends up sending our mail
   (matters for deliverability, separate from Route 53's forward DNS role).
6. **Cost** — we've been operating under a strict free/low-cost constraint so far
   (Brevo free tier, Zoho free tier, DigitalPlat free domain evaluated). Route 53
   is not free (domain registration + per-hosted-zone charges + per-query
   charges) — worth him flagging actual expected monthly cost, and whether a
   cloud emulator can validate the *setup* for free before we commit spend.
7. **Webhook reachability** — confirm nothing about Route 53 itself blocks or
   complicates exposing a stable HTTPS endpoint for Gmail Pub/Sub push and Stripe
   webhooks (this is really an EC2/hosting question, not DNS, but worth ruling out
   any AWS-specific gotcha, e.g. security groups, since he has AWS experience).

## 6. References (existing docs in this repo, for detail on any topic above)

- `CLOUDFLARE_TUNNEL_AND_EMAIL_TESTING_README.md` — tunnel setup, delegation failure, Spamhaus finding
- `CRON_AND_EMAIL_DELIVERABILITY_README.md` — cron/thread/connection concepts, load balancer misconception
- `EMAIL_DOMAIN_MIGRATION_README.md` — domain/subdomain strategy, provider comparison (Zoho/Brevo/SES/Mailgun)
- `EMAIL_OPEN_CLICK_TRACKING_README.md` — why tracking needs a public `web.base.url`
- `MASS_MAILING_INCIDENT_LOG.md` — concrete incident tying several of these issues together
- `WEBHOOK_INBOUND_MAIL_README.md` — Gmail Pub/Sub push webhook design, full migration plan
- `ZOHO_MAIL_SETUP_README.md` — actual DNS records currently live for `storeget.dpdns.org`
- `SNAILMAIL_MANUAL_LETTER_README.md`, `TEST_EMAIL_ADDRESSES_README.md` — testing tooling, not infra-relevant to Route 53
