from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    dearness_allowance = fields.Boolean(
        string='Dearness Allowance',
        help='Check this box if your company provide Dearness Allowance to employee')
