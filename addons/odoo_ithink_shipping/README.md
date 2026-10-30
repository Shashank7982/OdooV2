# iThink Logistics Shipping (odoo_ithink_shipping)

Integrates [iThink Logistics](https://www.ithinklogistics.com) into Odoo 18's
delivery carrier framework, using the `api_v3` REST API
(https://docs.ithinklogistics.com/).

## Features
- Delivery method provider `iThink Logistics`.
- Live rate estimation on sale orders (`rate/check.json`).
- One-click order booking + AWB assignment on validated deliveries
  (`order/add.json`).
- Shipping label and manifest PDF generation, stored as attachments
  (`shipping/label.json`, `shipping/manifest.json`).
- Shipment cancellation (`order/cancel.json`).
- Tracking status sync, manual button + cron every 2 hours
  (`order/track.json`).

## Configuration
1. Get your **Access Token** and **Secret Key** from your iThink Logistics
   account manager / dashboard.
2. Go to **Inventory / Sales > Configuration > Delivery > Shipping Methods**.
3. Create a new Shipping Method, set **Provider** to `iThink Logistics`.
4. On the **iThink Logistics Configuration** tab, fill in:
   - Access Token / Secret Key
   - Pickup Address ID (and optionally Return Address ID) — these come from
     your warehouse setup in the iThink Logistics dashboard, not from Odoo.
   - Preferred logistics partner (optional — leave blank to auto-assign).
   - Default package weight/dimensions used when product weight is not set.
5. Click **Test Connection** to verify credentials.
6. Enable **Use Staging Environment** while testing against
   `pre-alpha.ithinklogistics.com`; disable it to go live against
   `my.ithinklogistics.com`.

## Notes
- Credentials are stored on the delivery method and only visible to users in
  the `base.group_system` (Settings / Technical) group.
- The access token and secret key shown by the user were **not** stored in
  code — enter them directly in the Shipping Method form in the Odoo UI.
