from odoo import models, fields

class HospitalMedicine(models.Model):
    _name = 'hospital.medicine'
    _description = 'HospitalMedicine'

    product_name = fields.Char('Medicine Name')
    product_qty = fields.Char('Product Quantity')
    unit_price = fields.Char('Unit Price')
    total_price = fields.Char('Total Price')
