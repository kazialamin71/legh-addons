from odoo import models, fields

class HospitalMedicineLine(models.Model):
    _name = 'hospital.medicine.line'
    _description = 'Hospital Medicine Line'

    product_name = fields.Many2one('hospital.medicine', string='Medicine Name')
    hospital_medicine_line_item = fields.Many2one('hospital.admission', string='Medicine Info')
    product_qty = fields.Char('Product Quantity')
    unit_price = fields.Char('Unit Price')
    total_price = fields.Char('Total Price')
