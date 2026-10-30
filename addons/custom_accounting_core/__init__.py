from . import models
from . import wizard


def post_init_hook(env):
    """Add 'Employee Salary' and 'Miscellaneous Expenses' journals to the
    accounting dashboard (favorites) for every existing company, so they show
    up as cards next to Customer Invoices / Vendor Bills / Bank / Cash.

    Uses journal type 'purchase' (not 'general') because the dashboard kanban
    only renders the Due/This week/Late bar chart and To Pay/Late stats for
    sale/purchase-type journals — a 'general' journal renders as an empty
    card, same as Point of Sale with no sessions."""
    # DD/MM/YYYY throughout: res.lang.date_format drives every form/list/filter
    # widget and QWeb report's format_date() rendering, for every installed language.
    env['res.lang'].search([]).write({'date_format': '%d/%m/%Y'})

    JournalModel = env['account.journal']
    for company in env['res.company'].search([]):
        for code, name in (('SAL', 'Employee Salary'), ('MEXP', 'Miscellaneous Expenses'), ('RENT', 'Rent')):
            journal = JournalModel.search([
                ('code', '=', code),
                ('company_id', '=', company.id),
            ], limit=1)
            if journal:
                if not journal.show_on_dashboard:
                    journal.show_on_dashboard = True
            else:
                JournalModel.create({
                    'name': name,
                    'code': code,
                    'type': 'purchase',
                    'company_id': company.id,
                    'show_on_dashboard': True,
                })
