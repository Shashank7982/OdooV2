# Migrating Odoo Email Marketing from Gmail to a Custom Domain (DigitalPlat)

## Context

Currently, Odoo's Email Marketing app is configured to send/receive through a
personal Gmail SMTP/IMAP account. The goal is to move sending (and optionally
receiving) over to a free domain registered with **DigitalPlat**, so outgoing
marketing mail is branded as `@yourdomain.com` instead of `@gmail.com`.

This document captures the reasoning and setup path discussed, so it can be
revisited without re-deriving it.

---

## 1. What "Email Forwarding" in DigitalPlat actually does

DigitalPlat's dashboard offers **email forwarding**, which is often mistaken
for full mailbox hosting. It is not.

- Forwarding only redirects **inbound** mail sent to an address like
  `contact@yourdomain.com` into an existing inbox (e.g. Gmail).
- It does **not** provide SMTP or IMAP credentials.
- It cannot be used by Odoo to send mail *as* the domain — Odoo's Outgoing
  Mail Server needs real SMTP auth tied to the domain.
- Replying "as" the forwarded address from Gmail (via Gmail's "Send mail as")
  is cosmetic only — it doesn't carry proper SPF/DKIM alignment for the
  domain, so it doesn't help deliverability.

**Bottom line:** forwarding is useful only if you want a human to *read* mail
sent to a domain address inside an existing inbox. It is irrelevant to
Odoo's marketing-send requirement.

---

## 2. Why Gmail SMTP isn't the right long-term tool for marketing mail

Gmail free accounts allow **500 emails/day** (Google Workspace: ~2,000/day).
Staying under that limit does not make it safe for marketing use:

| Issue | Detail |
|---|---|
| ToS risk | Gmail's terms prohibit bulk/marketing emailing over SMTP, regardless of staying under the daily cap. Accounts can be flagged/suspended for bulk-pattern behavior even under 500/day. |
| Blast radius | If flagged, the *entire* Gmail account (personal + transactional mail) is affected, not just marketing. |
| No domain authentication | Gmail can't sign SPF/DKIM for a domain it doesn't manage — mail can't be sent *as* `you@yourdomain.com` with proper authentication through Gmail SMTP. |
| No visibility | No bounce/complaint/open tracking — Odoo's own bounce handling depends on this feedback, which Gmail doesn't expose. |

For small, infrequent sends, Gmail may continue to work without incident.
The case for migrating strengthens as list size and send frequency grow.

---

## 3. Subdomains — the actual lever for organizing this

A subdomain is just a DNS record under the existing domain (A/CNAME/MX/TXT).
DigitalPlat's DNS panel allows creating effectively unlimited subdomains at
no extra cost — no separate registration needed.

**Recommended pattern (reputation isolation):**

- Root domain (`yourdomain.com`) — reserved for personal/transactional use.
- Dedicated subdomain (e.g. `mail.yourdomain.com`) — used exclusively for
  Odoo marketing sends.

If the marketing subdomain ever gets flagged/blacklisted from bulk sending,
the root domain and any real mailboxes on it stay unaffected.

**Each subdomain is independent** — creating one does not auto-forward or
link it to anything. Per subdomain, you separately decide:

- **Sending-only** (e.g. marketing subdomain): needs SPF + DKIM + DMARC TXT
  records pointing at the chosen relay. No mailbox needed at all — bounces
  and replies are handled by the relay provider.
- **Receiving** (e.g. a support subdomain): needs an MX record pointing to
  a real mail host (Zoho, Google Workspace, etc.), or a forwarding rule if
  a real inbox isn't needed.

"Redirecting to different IDs" is optional and only relevant if a human
needs to read mail landing on a given subdomain — not required for
marketing sends.

---

## 4. Provider comparison

### Mailbox hosting (gives you a real inbox at `you@yourdomain.com`)

| Provider | Free tier for custom domain | SMTP/IMAP | Notes |
|---|---|---|---|
| Zoho Mail | Yes — up to 5 mailboxes, 5GB each | Yes | Best free option for a real inbox on the domain |
| Google Workspace | No (paid only, ~$6/user/mo) | Yes | Gmail-quality, but paid |
| Microsoft 365 | No (paid only, ~$6/user/mo) | Yes | Outlook equivalent of Workspace |
| Yahoo | No custom-domain product | — | Discontinued for most regions |

### SMTP relay (send-only, no inbox — best fit for marketing volume)

| Provider | Free tier | Limits | Notes |
|---|---|---|---|
| **Brevo** | Free forever | 300 emails/day, no card required | Best zero-cost option currently |
| Mailgun | Trial only | ~100/day for 3 months, then paid (~$15/mo+) | No longer meaningfully free |
| Amazon SES | Free tier | 62,000/month free *only if sent from EC2*; otherwise ~$0.10/1,000 | Requires AWS account + sandbox approval for production sending |

**Recommendation given free/no-cost priority:** Brevo for outgoing SMTP relay
(marketing subdomain), optionally paired with Zoho Mail free tier if a real
inbox is also wanted for replies.

---

## 5. DNS records needed per sending subdomain

Whichever relay/mailbox provider is chosen, they will supply exact values
for these records — paste them into DigitalPlat's DNS panel for the chosen
subdomain:

- **SPF** (TXT) — authorizes which servers may send as the subdomain.
- **DKIM** (TXT) — cryptographically signs outgoing mail.
- **DMARC** (TXT) — tells receiving servers what to do on SPF/DKIM failure.
- **MX** — only needed if the subdomain should also *receive* mail.

---

## 6. Next steps (not yet done)

- [ ] Decide: Brevo-only (send-only, no inbox) vs. Brevo + Zoho (send + a
      real inbox for replies).
- [ ] Pick the marketing subdomain name (e.g. `mail.yourdomain.com`).
- [ ] Create Brevo account, verify the chosen (sub)domain, obtain SPF/DKIM
      values.
- [ ] Add DNS records in DigitalPlat's DNS panel for that subdomain.
- [ ] Configure Odoo Settings → Technical → Outgoing Mail Servers with
      Brevo's SMTP credentials.
- [ ] If a real inbox is wanted, set up Zoho Mail free tier + MX record, and
      configure Odoo's Incoming Mail Server (IMAP) accordingly.
- [ ] Send a test campaign to a small list and verify deliverability
      (check spam placement, SPF/DKIM pass in received headers).
