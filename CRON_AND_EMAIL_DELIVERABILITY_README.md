# Why Our Marketing Emails Go to Spam, and How Our Background Jobs Actually Work

This is a plain-language writeup of two connected investigations: why campaign emails
sent from `agentsub7982@gmail.com` keep landing in spam, and whether running several
background jobs (payments, incoming mail, outgoing mail queue) at once can overload
the server. Both come back to the same root cause — we're running everything through
a personal Gmail account with no dedicated infrastructure — so they're documented
together.

---

## Part 1: Why emails go to spam

### What we checked

We looked up `gmail.com`'s DNS records, the ones mail servers everywhere check before
deciding whether to trust a message claiming to be from `@gmail.com`:

```
SPF record:   v=spf1 redirect=_spf.google.com
DMARC record: v=DMARC1; p=none; sp=quarantine; rua=mailto:mailauth-reports@google.com
```

**SPF (Sender Policy Framework)** is a DNS record that lists which mail servers are
allowed to send email claiming to be from a given domain. `gmail.com`'s SPF record
says, in effect, "only Google's own servers are allowed to send as gmail.com."

**DKIM (DomainKeys Identified Mail)** is a digital signature attached to outgoing
mail, cryptographically proving it really came from the domain it claims to be from,
and wasn't altered in transit.

**DMARC (Domain-based Message Authentication)** is the policy layer that tells
receiving mail servers what to do when SPF or DKIM checks fail for a domain (ignore
it, quarantine it, or reject it outright).

Because we're sending straight through `smtp.gmail.com` using the same
`agentsub7982@gmail.com` account as the "From" address, Google itself signs and
delivers the mail — so SPF, DKIM, and DMARC all technically pass. **Authentication is
not our problem.**

### The actual problem: reputation and behavior, not technical setup

Even one or two test emails, sent to people we've never emailed before, still land in
spam. That rules out "it's just a bulk-sending volume problem" and points to two
things layered on top of each other:

1. **No relationship history.** Gmail (and every other provider) heavily weighs
   whether the recipient has ever emailed us back, opened our mail, or added us as a
   contact. A first-ever email to a stranger, especially several in a short window,
   looks identical to spam from the filter's point of view — regardless of how
   correctly it's authenticated.

2. **Personal Gmail accounts aren't built for outreach or marketing.** A regular
   `@gmail.com` account behaving like a mailing list (sending similar content to many
   new people) is exactly the pattern spam filters are tuned to catch. This is by
   design on Google's side, not a misconfiguration on ours.

3. **Possible reputation damage already done.** An earlier batch of ~50 cold emails
   from this same account may have already suppressed its sending reputation
   provider-side. That's not permanent, but it doesn't recover instantly either —
   it can take days to weeks of clean sending behavior to recover.

4. **Odoo's email template itself can add to the problem.** Marketing emails sent
   from Odoo include an invisible open-tracking pixel and links rewritten through
   Odoo's own server (for click tracking). If the server sending those links has no
   reputation of its own (a generic cloud IP, no reverse DNS), that's one more signal
   working against us, on top of everything else.

### What actually fixes it

There is no code change or Odoo setting that fixes this, because the root issue is
that we don't own a domain. `gmail.com` belongs to Google — we can't add DNS records
to it, and Gmail was never meant to send outbound marketing/cold-outreach mail at
any volume.

The real fix is:

1. **Register our own domain** (roughly $10-15/year from any registrar).
2. **Set up SPF/DKIM/DMARC for that domain** — either through Google Workspace, or
   through a dedicated transactional/marketing email provider (Mailgun, Brevo,
   Amazon SES, SendGrid all offer free tiers and walk you through this).
3. If the recipients haven't opted in anywhere, that's a separate compliance issue
   (CAN-SPAM / GDPR) worth resolving regardless of deliverability.

Owning the domain also solves a second problem for free: those same providers offer
**inbound webhooks** — new mail gets pushed to us instantly via HTTP, instead of us
having to repeatedly check an inbox on a timer the way we do now.

---

## Part 2: How our background jobs (cron) actually work

We currently run several scheduled background jobs on the same Odoo instance: one
retries failed marketing inbound-mail processing, and Odoo's built-in ones handle
things like the outgoing email queue and payment-related follow-ups. The question
was: if several of these want to run at the same moment, does that overload the
server, and do we need a load balancer?

### The terms, explained

**`ir.cron`** — Odoo's internal model for a scheduled job. Every recurring background
task (send queued emails, fetch new mail, retry failed records, run payment
follow-ups) is a record in this model: it stores what code to run, how often, and
when it's next due. Think of it as Odoo's built-in version of a cron table.

**Worker** — a separate process Odoo spins up to handle incoming web requests. In
production ("multi-worker") mode, Odoo runs several of these processes in parallel so
multiple users can be served at once, instead of one request blocking everyone else.

**Cron thread** — similar idea, but for background jobs instead of web requests. A
fixed number of these threads exist, and every due `ir.cron` job has to wait for one
to be free before it can run.

**`--max-cron-threads`** — a server startup setting that caps how many background
jobs can literally execute at the same instant (default is 2). If three jobs are due
at once but only 2 threads exist, the third simply waits until a thread frees up. This
isn't a crash — it's a queue — but it does mean scheduling all our jobs to fire
together creates avoidable delays.

**`--workers`** — the equivalent setting for web-facing request handling: how many
parallel processes serve website/API traffic. This is separate from cron threads,
but both draw from the same server's CPU and memory, and both need database
connections.

**Database connection / `db_maxconn`** — every worker process and every active cron
thread needs its own open connection to the Postgres database while it's doing work.
`db_maxconn` is the ceiling Odoo enforces on how many of these it will open at once.
If `workers + max_cron_threads` adds up to more than `db_maxconn` allows, some
processes get refused a database connection and fail, even though the server itself
isn't necessarily overloaded.

**`max_connections` (Postgres)** — this is Postgres's own hard ceiling on total
simultaneous connections from *any* source, not just Odoo. `db_maxconn` in Odoo must
stay comfortably under this, with headroom for other tools (pgAdmin, backups,
monitoring) that also connect to the same database.

**Load balancer** — a piece of infrastructure that spreads incoming *web* traffic
across multiple servers/instances, so no single machine handles all the requests
alone. It solves horizontal scaling of HTTP traffic. It does **not** parallelize cron
jobs — Odoo already prevents the same job from double-running (it takes a database
lock before executing), and running cron across multiple balanced nodes doesn't
inherently give more cron throughput, just redundancy if one node goes down.

**`priority` (on `ir.cron`)** — a field that decides which job wins when several are
due to the same limited pool of cron threads at once. Lower number = runs first. Not
set by default, meaning Odoo currently treats "send marketing email" and "process a
payment" as equally urgent, purely on a first-come basis.

### Does running multiple cron jobs at once cause a problem?

Yes, in a specific, well-understood way — not a dramatic "server crashes" way, but a
"things silently queue up and important jobs wait behind unimportant ones" way:

- All cron jobs share the same small thread pool (`max_cron_threads`, default 2).
- A slow job (like the outgoing mail cron doing synchronous SMTP calls to a rate-
  limited Gmail server) occupies its thread for the entire duration of that call. It
  doesn't hand the thread back until it's done.
- If a time-sensitive job (payment reconciliation) becomes due while both threads are
  occupied by slower jobs, it has to wait — even though nothing has technically
  failed.
- Adding more cron jobs without raising `db_maxconn`/Postgres `max_connections` to
  match risks connection-pool exhaustion under load.

### Fixes, in priority order

1. **Set `priority`** on the payment-related cron(s) so they preempt lower-urgency
   jobs like marketing mail retries when both are due at once.
2. **Stagger the schedules** — don't let the mail queue, mail fetch, and payment cron
   all land on the same interval/minute; space them out.
3. **Scale `--max-cron-threads`, `--workers`, and `db_maxconn` together**, not in
   isolation, and only as far as actual CPU cores and Postgres `max_connections`
   support.
4. **Move heavy, slow jobs to a dedicated cron-only Odoo instance** (`--workers 0`,
   pointed at the same database) if volume grows — this keeps bulk mail sending or
   payment batch jobs from ever competing with real-time website traffic on the main
   instance. This is the actual "scale it out" answer, not a load balancer.
5. **Reduce how long each run takes**, rather than just adding more threads — smaller
   batch sizes for the mail queue, and (tying back to Part 1) moving off synchronous
   Gmail SMTP to a proper email provider with a fast API, so each cron run finishes
   quickly instead of holding a thread hostage.

---

## Bottom line

Both issues trace back to the same gap: we're running production email sending and
scheduled jobs on infrastructure (a personal Gmail account, unconfigured cron
priorities) that wasn't built for it. The spam problem needs an owned domain with
proper email authentication; the cron-contention problem needs job prioritization and
right-sized thread/connection limits — not a load balancer. Neither requires a major
rebuild, just proper configuration once we have a domain in place.
