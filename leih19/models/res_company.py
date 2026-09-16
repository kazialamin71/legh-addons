from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    lab_report_disclaimer_html = fields.Html(
        'Lab Report Disclaimer', sanitize=False,
        help='Printed at the bottom of every lab report whose test has '
             '"Print Disclaimer" ticked. A department can override it.')
