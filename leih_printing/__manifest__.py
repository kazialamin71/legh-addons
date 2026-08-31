{
    'name': 'LEIS Counter Printing',
    'summary': 'Print bills, receipts and admission forms straight to the '
               'counter printer instead of downloading a PDF',
    'description': """
LEIS Counter Printing
=====================

Every report in this system was a ``qweb-pdf``, so pressing Print saved a file.
At a billing counter that is four actions per bill -- print, open, Ctrl+P,
close -- and a Downloads folder with three hundred ``Bill - MR-00123.pdf`` in it
by the end of the day.

This adds one setting per user, **Print via**, and routes every PDF report
through it:

``This computer``
    The PDF is handed to the browser, which prints it on whatever printer that
    PC is set to use. This is the option for a printer plugged into the counter
    PC by USB, because the server cannot reach one of those. With Chrome started
    as ``chrome.exe --kiosk-printing`` there is no dialog at all: the paper just
    comes out.

``Printer on the server``
    Odoo renders the PDF and hands it to a CUPS queue on the server. Nothing
    reaches the browser at all. This is the option for the shared floor printers,
    and it is the only one that lets a document be printed *somewhere else* --
    a lab report sent to the lab printer from the front desk.

``Download the PDF``
    What it did before, kept as an escape hatch.

Nothing about the reports themselves changes: the same wkhtmltopdf output is
produced either way, so every existing layout prints exactly as it did.
""",
    'version': '19.0.1.0.0',
    'author': 'Kazi Alamin',
    'category': 'Technical',
    # `web` for the backend assets and the widgets used in the views. Nothing
    # LEIS-specific: this deliberately applies to every PDF report in the
    # database, so staff learn one behaviour instead of two.
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'views/printing_printer_views.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leih_printing/static/src/js/print_action.js',
        ],
    },
    'license': 'LGPL-3',
    'application': False,
}
