{
    'name': 'LEIS Accounting',
    'summary': 'Post bill & admission revenue/payments to the GL (journal entries)',
    'version': '19.0.1.6',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19', 'indoor_management', 'leih_admission', 'leih_patient', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/accounting_config_views.xml',
        'views/income_source_views.xml',
        'views/account_buttons_views.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
