# GSTIN Sandbox Verification for Odoo 18

This addon verifies a partner GSTIN through Sandbox's GST Public API.

## Test setup

1. Create a Sandbox developer account.
2. Create test API credentials. Test keys use the `key_test` prefix.
3. In Odoo open **Settings > Companies > GST Invoice Details**.
4. Enable **GSTIN Verification**.
5. Select **Test** and enter the Sandbox test API key and secret.
6. Open an Indian contact, enter `vat` (GSTIN), and click **Verify GSTIN**.

The test environment is `https://test-api.sandbox.co.in` and uses test data. The production environment is `https://api.sandbox.co.in` and is billed by Sandbox.

## Implemented behavior

- Authenticates at `/authenticate` and caches the access token for 24 hours.
- Calls `/gst/compliance/public/gstin/verify` with the partner GSTIN.
- Stores legal name, trade name, PAN, state, registration date, status and transaction ID.
- Marks a partner **Verified** only when `validGstin == true` and API status is `Active`.
- Stores an error state when the network/API call fails.
- Keeps the raw response for audit/debugging.

## Important

GSTIN verification confirms registration details. It does not prove that the person entering the GSTIN owns or controls the company.
