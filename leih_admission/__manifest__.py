{
    'name': 'LEIS Hospital Admission',
    'summary': 'IPD admission: unified charges, payments and statement (Phase A: payments)',
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19'],
    'data': [
        'security/ir.model.access.csv',
        'reports/admission_form_report.xml',
        'reports/admission_statement_report.xml',
        'reports/admission_discharge_report.xml',
        'views/hospital_admission_charge_views.xml',
        'views/hospital_admission_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leih_admission/static/src/css/admission.css',
        ],
    },
    'license': 'LGPL-3',
    'application': False,
}
