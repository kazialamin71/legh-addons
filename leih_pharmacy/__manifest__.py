{
    'name': 'LEIS Pharmacy (IPD)',
    'summary': 'Indoor pharmacy: requisition -> issue (stock out) -> charge-to-room, with returns',
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih_admission', 'stock'],
    'data': [
        'security/pharmacy_security.xml',
        'security/ir.model.access.csv',
        'data/pharmacy_sequence.xml',
        'reports/pharmacy_requisition_report.xml',
        'views/pharmacy_requisition_views.xml',
        'views/hospital_admission_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'application': True,
}
