from odoo import models, fields

class HospitalBed(models.Model):
    _name = 'hospital.bed'
    _description = 'HospitalBed'

    name = fields.Char('Bed Number')
    bed_type = fields.Selection(
        [('general', 'General Bed'),
         ('cabin', 'Cabin'),
         ('icu', 'ICU'),
         ('nicu', 'NICU'),
         ('hdu', 'HDU'),
         ('other', 'Other')],
        string='Bed Type', default='general', required=True,
        help='Drives the charge service type and per-unit income reporting (ICU/NICU/Cabin).')
    bed_qty = fields.Char('Bed Quantity')
    perday_charge = fields.Float('Per Day Charge')
    total_amount = fields.Float('Total Amount')
