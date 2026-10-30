# Shiprocket Shipping — Odoo 18 Addon

Custom delivery-carrier integration connecting Odoo Inventory/Sales to
[Shiprocket](https://shiprocket.in) (`apiv2.shiprocket.in`). Built on Odoo's
standard `delivery.carrier` provider framework — same pattern as
core connectors like DHL/FedEx.

## Status — actively tested, one external blocker remaining

Credentials are configured and connection-tested successfully. A real
end-to-end test (quote → confirm → validate → send to shipper) got all the
way to Shiprocket accepting the order data, then stopped on:

```
Shiprocket error: KYC verification is mandated for your account to ship
an order. Please complete your KYC to proceed further.
```

This is a **Shiprocket account-level requirement**, not an Odoo/addon issue
— nothing left to fix in code until KYC is completed on the Shiprocket
dashboard side. See "Testing history" below for the full trail.

## Features

### Rate quoting
- On the sale order, selecting a Shiprocket-backed delivery method calls the
  Shiprocket **Serviceability API** with pickup/delivery pincode, weight, and
  COD flag.
- Returns the **cheapest available courier's rate** as the shipping price.
- **Verified working** — a real test order (Hyderabad delivery address)
  returned a live quote of $72.36 as a "Shiprocket Shipping Charges" line.

### Booking / shipment creation
Triggered by the **"Send to Shipper"** button, which appears on a picking's
**Additional Info** tab once it's been **validated** (state = Done):
1. Creates the order on Shiprocket (`/orders/create/adhoc`).
2. Assigns an AWB / courier (`/courier/assign/awb`).
3. Requests pickup (`/courier/generate/pickup`).
4. Auto-generates and attaches the shipping **label** and **manifest** PDFs.
5. Stores the tracking number as `carrier_tracking_ref`, plus Shiprocket's
   own `shipment_id` / `order_id` on the picking.

**Blocked on:** Shiprocket account KYC (see Status above) — payload is
confirmed valid, booking itself hasn't completed yet.

### Test Connection button
New: a **"Test Connection"** button on the delivery method's Shiprocket
Configuration tab. It:
- Forces a fresh login (ignores any cached token) to genuinely re-validate
  email/password
- If a Pickup Location Nickname is set, cross-checks it against your real
  Shiprocket pickup addresses and warns on a mismatch
- Warns explicitly if no pickup location is set at all

**Verified working** — confirmed successful authentication.

### Cancellation
- The standard **"Cancel"** delivery button calls Shiprocket's
  cancel-shipment (or cancel-order, if no AWB yet) endpoint and logs a note
  on the picking's chatter. Not yet tested (nothing to cancel until a
  booking succeeds).

### Tracking sync
- **Manual**: "Sync Status" button on the picking form.
- **Automatic**: a scheduled action runs every 2 hours.
- Not yet tested (nothing to sync until a booking succeeds).

### Labels & manifests on demand
- "Get Label" / "Get Manifest" buttons for re-generating after booking.
- Not yet tested (same reason).

### Tracking link
- Opens `https://shiprocket.co/tracking/<awb>`. Not yet tested.

## Configuration UI

**Inventory / Sales → Configuration → Delivery → Shipping Methods**
→ create/edit a method → set **Provider = Shiprocket**.

**Shiprocket Configuration** tab:

| Field | Purpose | Current test state |
|---|---|---|
| Shiprocket Email / Password | Account login | ✅ set, connection-verified |
| Pickup Location Nickname | Must match a Shiprocket pickup address nickname exactly | ✅ set to `work`, verified matching |
| Preferred Courier ID | Optional; blank = auto-select | not set |
| Default Weight / Length / Width / Height | Fallback package dimensions | using defaults (0.5kg / 10×10×10cm) |

**Delivery Product**: set to a dedicated **"Shiprocket Shipping Charges"**
service product (created specifically for this, no company restriction, no
attached documents) — the original default ("Customizable Desk") caused a
multi-company **Access Error** because it had a document attachment scoped
to a different company. If you ever see that error again on a different
setup, swap the Delivery Product to a clean company-agnostic product the
same way.

## Testing history — issues found and fixed

1. **Instagram/Facebook-style URL pasted into handle fields** *(this was
   actually a `competitor_analysis` issue, not Shiprocket — unrelated)*.
2. **"Access Error" on Add Shipping** — delivery method's product had a
   document attachment restricted to a different company. Fixed by creating
   a clean, company-agnostic "Shiprocket Shipping Charges" product.
3. **"Shiprocket error: Oops! Invalid Data."** on Send to Shipper — root
   cause found by replaying the exact payload directly against Shiprocket's
   API: missing `billing_last_name` field entirely, and empty `billing_phone`
   (test customer had no phone number). Fixed:
   - Code now always sends `billing_last_name` (derived by splitting the
     partner's name)
   - Code now raises a clear Odoo `UserError` up front if the partner has no
     phone/mobile set, instead of letting Shiprocket's cryptic generic error
     surface
4. **"Shiprocket error: KYC verification is mandated..."** — current
   blocker, account-level, not code. Waiting on KYC completion in the
   Shiprocket dashboard.

## How to resume testing once KYC is done

1. Shiprocket dashboard → complete KYC (PAN, GSTIN, bank details for COD
   remittance, business docs as prompted)
2. In Odoo, go back to the test delivery (**IN Co/OUT/00001**, or create a
   fresh one) → **Additional Info** tab → click **"Send to Shipper"** again
3. On success: check for a **Tracking Reference (AWB)** and
   **Shiprocket Status** appearing on the picking, and label/manifest PDFs
   under Attachments
4. Then test **Sync Status**, **Get Label**, **Get Manifest**, and
   **Cancel** to close out the remaining untested features

## Files

```
delivery_shiprocket/
├── __manifest__.py
├── models/
│   ├── shiprocket_request.py        # Low-level REST client (auth, orders, AWB, labels, tracking)
│   ├── delivery_carrier.py          # delivery.carrier extension: rate/send/cancel/tracking-link hooks,
│   │                                 # Test Connection action
│   └── stock_picking.py             # shipment/order id + status fields, label/manifest/sync actions, cron entrypoint
├── views/
│   ├── delivery_shiprocket_views.xml  # Shiprocket Configuration tab + Test Connection button
│   └── stock_picking_views.xml        # Status field + Sync/Label/Manifest buttons on picking form
└── security/
    └── ir.model.access.csv
```

## Dependencies
`delivery`, `stock_delivery` (both core Odoo modules).

## Known caveats / not yet done
- **KYC-gated** — can't complete a real booking test until Shiprocket
  approves your account's KYC (see Status above).
- **COD amount / partial-COD reconciliation** is not handled — only a
  binary COD vs. Prepaid flag, based on the sale order's payment term name
  containing "cod".
- **No inbound webhook** — tracking updates are pull-based (cron + manual
  button), not push-based.
- **Multi-package shipments** (more than one box per picking) are not
  modeled — each picking maps to a single Shiprocket shipment.
- **Cancellation, tracking sync, label/manifest regeneration** are
  implemented but not yet exercised against a real booking — verify once
  KYC is cleared.
