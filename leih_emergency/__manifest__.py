{
    'name': 'LEIS Emergency (ED)',
    'summary': 'Emergency department: triage, ED board, consumables and '
               'investigations, disposition to discharge or admission',
    'description': """
Emergency Department
====================

An ED encounter is not an admission that happens to be urgent: most patients are
treated and sent home, and never occupy a bed. This module therefore models the
encounter (``emergency.case``) in its own right, and produces a hospital
admission only when the disposition is actually "Admitted".

Flow: Arrival -> Triage -> Treatment -> Disposition.
""",
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19'],
    'data': [
        'security/ir.model.access.csv',
        'data/emergency_sequence.xml',
        'wizard/emergency_payment_wizard_views.xml',
        'wizard/emergency_disposition_wizard_views.xml',
        'views/emergency_case_views.xml',
        'reports/emergency_case_report.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leih_emergency/static/src/css/emergency.css',
        ],
    },
    'license': 'LGPL-3',
    'application': False,
}
