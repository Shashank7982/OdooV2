"""Analyze active cart and partner emails to see why admin@yourcompany.example.com is being used."""
import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo18db'
username = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    print("Authentication failed")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# 1. Search for partner 'Shashank'
partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
    [[('name', 'ilike', 'Shashank')]],
    {'fields': ['name', 'email', 'user_ids']})
print("Partners named 'Shashank':")
for p in partners:
    print(f"  ID: {p['id']}, Name: {p['name']}, Email: {p['email']}, Users: {p['user_ids']}")

# 2. Check the active sales orders (carts)
orders = models.execute_kw(db, uid, password, 'sale.order', 'search_read',
    [[('state', '=', 'draft')]],
    {'fields': ['name', 'partner_id', 'partner_invoice_id', 'amount_total']})
print("\nDraft Sales Orders (Active Carts):")
for o in orders:
    partner_info = models.execute_kw(db, uid, password, 'res.partner', 'read',
        [[o['partner_id'][0]], ['name', 'email']])
    invoice_partner_info = models.execute_kw(db, uid, password, 'res.partner', 'read',
        [[o['partner_invoice_id'][0]], ['name', 'email']])
    print(f"  Order: {o['name']}, Total: {o['amount_total']}")
    print(f"    Partner: {partner_info[0]['name']} (Email: {partner_info[0]['email']})")
    print(f"    Invoice Partner: {invoice_partner_info[0]['name']} (Email: {invoice_partner_info[0]['email']})")
