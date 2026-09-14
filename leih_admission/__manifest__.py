{
    'name': 'LEIS Hospital Admission',
    'summary': 'IPD admission: unified charges, payments and statement (Phase A: payments)',
    'version': '19.0.1.1',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19'],
    'data': [
        'security/ir.model.access.csv',
        'data/admission_charge_type_data.xml',
        'views/admission_charge_type_views.xml',
        'reports/admission_form_report.xml',
        'reports/admission_statement_report.xml',
        'reports/admission_detail_report.xml',
        'reports/admission_discharge_report.xml',
        'views/hospital_admission_charge_views.xml',
        'views/hospital_admission_views.xml',
        'views/money_receipt_print_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leih_admission/static/src/css/admission.css',
        ],
    },
    'license': 'LGPL-3',
    'application': False,
}
