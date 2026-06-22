from odoo import models, fields

class Discount(models.Model):
    _name = 'discount'
    _description = 'Discount'

    name = fields.Char('Discount Number')
    date = fields.Datetime('Date', readonly=True, default=None)
    admission_id = fields.Many2one('leih.admission', string='Admission ID')
    bill_no = fields.Many2one('bill.register', string='Bill No')
    patient_name = fields.Char('Patient Name', required=True)
    mobile = fields.Char('Mobile Number', required=True)
    total_discount = fields.Float('Total Discount')
    amount = fields.Integer('Amount')
    state = fields.Selection([('pending', 'Pending'), ('approve', 'Approved'), ('cancel', 'Cancelled')], 'State', default='pending', readonly=True)
    discount_line_id = fields.One2many('discount.line', 'discount_id', required=True)
