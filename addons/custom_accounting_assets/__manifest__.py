{
    'name': 'Custom Accounting Fixed Assets',
    'category': 'Accounting/Accounting',
    'summary': 'Asset categories, depreciation schedules, and automatic depreciation entries',
    'description': """
Custom Accounting Fixed Assets
==================================
Part of custom_full_accounting. Built from scratch (Enterprise's
account_asset is not present in this Community instance).

- Asset categories with default accounts and depreciation method
- Straight-line and declining-balance depreciation
- Auto-generated monthly depreciation schedule
- A daily cron posts depreciation entries once their date is reached
- Asset disposal (writes off remaining value)
- Create an asset directly from a posted vendor bill line
""",
    'version': '1.0',
    'depends': ['account', 'mail', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/account_asset_category_views.xml',
        'views/account_asset_views.xml',
        'views/account_move_views.xml',
        'wizard/account_asset_sale_wizard_views.xml',
        'wizard/account_asset_transfer_wizard_views.xml',
        'wizard/account_asset_revaluation_wizard_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
