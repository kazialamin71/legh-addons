from odoo import models, fields

class LeihAdmissionLine(models.Model):
    _name = 'leih.admission.line'
    _description = 'LeihAdmissionLine'

    name = fields.Many2one('examination.entry', string='Item Name', ondelete='cascade')
    leih_admission_id = fields.Many2one('leih.admission', string='Information')
    department = fields.Char('Department')
    price = fields.Float('Price')
    discount = fields.Float('Discount')
    flat_discount = fields.Integer('Flat Discount')
    total_discount = fields.Integer('Total Discount')
    discount_percent = fields.Integer('Discount Percent')
    total_amount = fields.Float('Total Amount')
