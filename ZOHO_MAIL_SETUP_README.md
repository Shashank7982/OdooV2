# Zoho Mail Setup for Odoo Email Marketing

Domain: `storeget.dpdns.org` (DNS hosted on deSEC)
Zoho data center: India (`.in`) — confirmed via `zmverify.zoho.in`
Zoho mailbox: `admin@storeget.dpdns.org`

## 1. Domain verification

Added TXT record at the domain root to prove ownership to Zoho.

- Record type: TXT
- Subname: blank (root/apex — deSEC does not accept `@`, leave the field empty)
- Value: `zoho-verification=zb53769737.zmverify.zoho.in`

Note: deSEC allows only **one TXT RRset per subname**, but that RRset can hold multiple
string values. The verification string was added as an additional value inside the
existing root TXT record (which already held `brevo-code:...` from a previous provider).

## 2. MX records (mail routing)

Domain was previously using ImprovMX (`mx1.improvmx.com`) for forwarding. Since the goal
was to get a real Zoho mailbox (SMTP + IMAP), MX was switched to Zoho:

| Type | Host | Value | Priority |
|------|------|-------|----------|
| MX | @ | mx.zoho.in | 10 |
| MX | @ | mx2.zoho.in | 20 |
| MX | @ | mx3.zoho.in | 50 |

The old ImprovMX MX record was replaced (not kept alongside).

## 3. SPF

SPF must be a single TXT value per domain — cannot have two `v=spf1` strings.

- Old value (ImprovMX): `v=spf1 include:spf.improvmx.com ~all`
- New value (Zoho): `v=spf1 include:zoho.in ~all`

This was edited in place inside the existing root TXT record, replacing the old SPF
string among its other values (verification code, etc. left untouched).

## 4. DKIM

Added as a TXT record at the host Zoho specified:

- Subname: `zmail._domainkey`
- Value: `v=DKIM1; k=rsa; p=<long key Zoho provided>`

## 5. DMARC (existing, not yet updated)

`_dmarc` TXT record currently still points to the old Brevo reporting address:

```
v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com
```

**TODO**: update `rua` to a mailbox you actually control, e.g.
`rua=mailto:admin@storeget.dpdns.org`, since the Brevo address is stale.

## 6. Zoho mailbox / app password

- 2FA enabled on the Zoho account (required before app passwords are available).
- Generated an app-specific password (Zoho Mail → Security → App Passwords) —
  this is used for SMTP/IMAP auth, not the normal login password.

## 7. SMTP / IMAP server details (India data center)

- SMTP: `smtp.zoho.in`, port `465`, connection security **SSL/TLS**
  (port 587 + STARTTLS was tried first but caused
  `smtplib.SMTPServerDisconnected: please run connect() first` on real sends,
  even though "Test Connection" passed — likely a STARTTLS/Windows Python 3.12
  interaction. Switching to port 465 SSL/TLS fixed it.)
- IMAP: `imap.zoho.in`, port `993`
- POP (not used): `pop.zoho.in`, port `995`
- IMAP/SMTP access must be explicitly enabled per-account in Zoho Mail →
  Settings → Mail Accounts.

## 8. Odoo configuration

**Settings → Technical → Email → Outgoing Mail Servers**
- SMTP Server: `smtp.zoho.in`
- Port: `465`
- Connection Security: SSL/TLS
- Username: `admin@storeget.dpdns.org`
- Password: Zoho app-specific password
- Test Connection: passing
- Priority: set lower than other configured servers (Brevo, etc.) if Zoho should
  be preferred.

## 9. Known issue found: sender/From mismatch

A test mailing failed/cancelled because the mailing's **From** address was
`"Mitchell Admin" <marketing@storeget.dpdns.org>` (Odoo's leftover demo company
email), while the SMTP auth user is `admin@storeget.dpdns.org`. Zoho rejects
sends where the From address isn't a mailbox/alias you're authorized to use.

**Fix (pending)**: update the Company / user email in Odoo to
`admin@storeget.dpdns.org` (or add `marketing@storeget.dpdns.org` as a verified
alias in Zoho if a separate marketing sender address is actually wanted).

## 10. Deliverability notes

- Domain is brand new — no sending reputation yet. Gmail has already spam-blocked
  at least one test send (`550 5.7.1 ... likely unsolicited mail`), even though
  DKIM/SPF were in place. This is expected for a new domain and should improve
  with time/volume ("warm-up").
- Avoid generic one-word subjects/bodies ("test") in test sends — they read as
  spam probes to filters.
- Check **Google Postmaster Tools** (postmaster.google.com) once available to
  monitor domain reputation with Gmail specifically.
- Zoho SMTP relay does not create entries in Zoho's own **Sent** folder — that's
  only populated by mail composed in Zoho's webmail UI, not third-party SMTP
  submissions like Odoo's.

## Outstanding TODOs

- [ ] Fix sender address mismatch (`marketing@` vs `admin@`) so mailings don't
      get cancelled.
- [ ] Update `_dmarc` record's `rua` address away from the stale Brevo address.
- [ ] Decide whether to keep or remove old Brevo DNS records
      (`brevo1._domainkey`, `brevo2._domainkey` CNAMEs, `brevo-code` TXT value)
      once Brevo is fully retired.
- [ ] Monitor Gmail deliverability over the next few days as domain reputation
      builds; consider Google Postmaster Tools.
