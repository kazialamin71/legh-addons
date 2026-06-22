{
    'name': 'LEIS Patient Partner',
    'summary': 'Link each patient to a res.partner for invoicing / POS / AR',
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19', 'contacts'],
    'data': [
        'data/patient_partner_data.xml',
        'views/patient_info_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'application': False,
}
