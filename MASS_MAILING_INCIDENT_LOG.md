# Mass Mailing Incident Log — 2026-08-17

Mailing: id 76, subject "admin", database `odoo18db`. 178 recipients across
mailing lists "check bulk (169)" and "Testing (9)".

## Timeline

- **03:41:12** — Mailing dispatched (`mailing_mailing.state` → `done`,
  `sent_date` set). Only a partial batch actually processed before halting:
  33 cancelled (blacklisted contacts), 145 left in `outgoing` trace status,
  0 actually sent.
- **~09:1x AM (user-reported)** — Noticed mailing showed "Sent" stage but
  "0 emails have been sent" in the UI banner.

## Root cause #1 — cron misconfigured to run once/day

`ir_cron` id 33, "Mail Marketing: Process queue" (the job that actually
dispatches queued mass-mailing emails), was set to:

```
interval_number = 1
interval_type   = days
lastcall        = 2026-08-17 03:41:13
nextcall        = 2026-08-17 13:05:02   (~9.5 hours away)
```

It fired once at mailing-creation time, processed the first chunk, then
wouldn't run again for ~9.5 hours — so the remaining 145 recipients sat idle
indefinitely. This is not the standard Odoo default cadence for this job.

**Fix applied:**

```sql
UPDATE ir_cron
SET interval_number = 1, interval_type = 'minutes', nextcall = now()
WHERE id = 33;
```

After this, the queue began draining automatically every ~1 minute:

| Time (approx) | sent | error | outgoing | cancel |
|---|---|---|---|---|
| 03:44 | 0 | 0 | 145 | 33 |
| ~03:46 | 28 | 0 | 116 | 33 |
| ~03:48 | 45 | 0 | 81 | 33 |
| ~03:52 | 52 | 12 | 81 | 33 |
| ~03:53+ | 52 (stalled) | 12 (stalled) | 81 (stalled) | 33 |

Note: Odoo's `ir_cron.interval_type` has no seconds-level granularity
(minutes is the finest unit), and the scheduler's own polling loop runs on
roughly a 1-minute cadence regardless — so 1 minute is effectively the
practical floor.

## Root cause #2 — sending stalled again after ~52 sends

After reaching 52 sent / 12 errored, progress **flatlined**: the cron kept
firing (`lastcall` kept advancing every ~1 min) but no new `mail.mail`
records were created and no new trace status changes occurred — consistent
with the outgoing SMTP connection failing at connect/auth time, before Odoo
even logs a per-message failure.

**Contributing factor identified:** this mailing has no explicit
`mail_server_id` set, so it falls back to the **lowest-sequence configured
server**:

```
id=25  "Zoho SMTP"  smtp.zoho.in  admin@storeget.dpdns.org   (sequence 1)
```

`storeget.dpdns.org` is the same domain independently confirmed earlier to
be **Spamhaus DBL-listed** (via the parent `dpdns.org` free dynamic-DNS
domain — see `CLOUDFLARE_TUNNEL_AND_EMAIL_TESTING_README.md`). Working
theory: a meaningful fraction of the 169 real recipients' mail servers
reject/bounce mail from this domain because of the listing, and Zoho's
outbound relay throttles or temporarily suspends sending on the account
after detecting a burst of bounces/rejections, to protect its own sending
reputation. This would explain sends succeeding for the first ~52
recipients then halting completely with no further error detail logged.

**Not yet confirmed:** the exact SMTP error text, since Odoo logs to stdout
in the running server's console window (no `logfile` set in `odoo.conf`,
and `ir_logging`/DB logging is not enabled) — it wasn't accessible for this
investigation. Whoever has the terminal window open should check it for
`ERROR`/`smtplib` lines timestamped around 03:52–onward.

## Open items / recommended next steps

1. **Real root fix:** stop sending from `storeget.dpdns.org` — it's a free
   shared subdomain (`dpdns.org`) that's Spamhaus-blocklisted at the parent
   level and will keep causing this same failure mode. Send from a real,
   owned domain instead.
2. **Immediate workaround:** set mailing id 76's `mail_server_id` to a
   different configured server (`Brevo SMTP` id 23, or `Gmail SMTP` id 1)
   instead of relying on the Zoho fallback, then retry the remaining 81
   `outgoing` recipients.
3. Consider setting `ir_cron` id 33 back to a sane always-on interval
   (1 minute, as currently set) permanently rather than reverting to the
   1/day misconfiguration — verify nothing else changed it back.
4. Enable a `logfile` in `odoo.conf` so future incidents like this can be
   diagnosed without needing live console access.
