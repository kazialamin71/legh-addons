{
    'name': 'LEIS Hospital Admission',
    'summary': 'IPD admission: unified charges, payments and statement (Phase A: payments)',
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19'],
    'data': [
        'security/ir.model.access.csv',
        'reports/admission_statement_report.xml',
        'views/hospital_admission_charge_views.xml',
        'views/hospital_admission_views.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
