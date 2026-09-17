{
    'name': 'LEIS Medicine Catalogue',
    'summary': 'Generic (molecule) group and supplier on medicines, supplier-driven '
               'purchasing, supplier-wise stock and generic-name search in the POS',
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['product', 'purchase', 'stock', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/medicine_generic_views.xml',
        'views/product_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_quant_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'leih_medicine_catalog/static/src/js/pos_generic_search.js',
        ],
    },
    'license': 'LGPL-3',
    'application': False,
}
