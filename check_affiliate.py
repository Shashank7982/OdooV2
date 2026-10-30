"""Diagnostic: check affiliate module models and views in the running Odoo instance."""
import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo18db'
username = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    print("Authentication failed")
    exit(1)

models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')

# 1. Check sale.affiliate fields
print("=== sale.affiliate fields ===")
try:
    fields_info = models.execute_kw(
        db, uid, password, 'sale.affiliate', 'fields_get', [],
        {'attributes': ['string', 'type']}
    )
    for fname, fval in sorted(fields_info.items()):
        print("  %s: %s (%s)" % (fname, fval['type'], fval['string']))
except Exception as e:
    print("  ERROR: %s" % e)

# 2. Check affiliate.click fields
print("\n=== affiliate.click fields ===")
try:
    fields_info = models.execute_kw(
        db, uid, password, 'affiliate.click', 'fields_get', [],
        {'attributes': ['string', 'type']}
    )
    for fname, fval in sorted(fields_info.items()):
        print("  %s: %s (%s)" % (fname, fval['type'], fval['string']))
except Exception as e:
    print("  ERROR: %s" % e)

# 3. Check affiliate.commission fields
print("\n=== affiliate.commission fields ===")
try:
    fields_info = models.execute_kw(
        db, uid, password, 'affiliate.commission', 'fields_get', [],
        {'attributes': ['string', 'type']}
    )
    for fname, fval in sorted(fields_info.items()):
        print("  %s: %s (%s)" % (fname, fval['type'], fval['string']))
except Exception as e:
    print("  ERROR: %s" % e)

# 4. Check affiliate.withdrawal fields
print("\n=== affiliate.withdrawal fields ===")
try:
    fields_info = models.execute_kw(
        db, uid, password, 'affiliate.withdrawal', 'fields_get', [],
        {'attributes': ['string', 'type']}
    )
    for fname, fval in sorted(fields_info.items()):
        print("  %s: %s (%s)" % (fname, fval['type'], fval['string']))
except Exception as e:
    print("  ERROR: %s" % e)

# 5. Check installed modules
print("\n=== Affiliate module install status ===")
try:
    modules = models.execute_kw(
        db, uid, password, 'ir.module.module', 'search_read',
        [[('name', 'in', ['website_sale_affiliate', 'website_sale_affiliate_custom'])]],
        {'fields': ['name', 'state', 'latest_version']}
    )
    for m in modules:
        print("  %s: state=%s version=%s" % (m['name'], m['state'], m['latest_version']))
except Exception as e:
    print("  ERROR: %s" % e)

# 6. Try to read affiliate.click list (this triggers the Oops error)
print("\n=== Try reading affiliate.click records ===")
try:
    clicks = models.execute_kw(
        db, uid, password, 'affiliate.click', 'search_read',
        [[]],
        {'fields': ['affiliate_id', 'click_date', 'ip_address', 'url', 'converted', 'sale_order_id'], 'limit': 5}
    )
    print("  OK. Records found: %d" % len(clicks))
except Exception as e:
    print("  ERROR: %s" % e)

# 7. Check if there are any broken views
print("\n=== Check ir.ui.view for affiliate ===")
try:
    views = models.execute_kw(
        db, uid, password, 'ir.ui.view', 'search_read',
        [[('model', 'in', ['affiliate.click', 'affiliate.commission', 'affiliate.withdrawal', 'sale.affiliate'])]],
        {'fields': ['name', 'model', 'type', 'active'], 'limit': 50}
    )
    for v in views:
        print("  %s | model=%s | type=%s | active=%s" % (v['name'], v['model'], v['type'], v['active']))
except Exception as e:
    print("  ERROR: %s" % e)
