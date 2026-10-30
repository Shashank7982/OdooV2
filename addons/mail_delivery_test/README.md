# Mail Delivery Test Template

This small Odoo 18 module adds two simple test templates:

1. **Delivery Test - Sales Order** (`mail.template`) — usable from a sales
   order's "Send by Email" dialog.
2. **Delivery Test Template** (`mailing.mailing`, marked as Favorite) —
   appears in the **Email Marketing** app's template gallery, selectable when
   starting a new mailing/campaign.

Both templates intentionally use a short subject, basic HTML, no images, no
tracking links, and no attachments. They are intended for sending a test
message to your own Gmail address while diagnosing delivery and spam
placement.

## Install

1. Restart Odoo.
2. Enable Developer Mode.
3. Update the Apps List.
4. Install **Mail Delivery Test Template** (this now depends on
   `sale_management` and `mass_mailing`).
5. For the sales-order template: open a sales order and use
   **Delivery Test - Sales Order**.
6. For the mailing template: open the **Email Marketing** app → New → the
   template gallery should include **Delivery Test Template**.

This template does not configure SMTP and does not guarantee inbox placement;
SPF, DKIM, DMARC, sender reputation, and sending volume still matter.
