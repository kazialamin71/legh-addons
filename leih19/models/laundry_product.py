from odoo import models, fields

class LaundryProduct(models.Model):
    _name = 'laundry.product'
    _description = 'LaundryProduct'

    name = fields.Char('Name', required=True)
    color = fields.Char('Color', required=True)
    quantity = fields.Integer('Quantity', required=True)
    type = fields.Selection([('general', 'General Purpose Linen'), ('patient', 'Patient Linen'), ('ward', 'Ward Linen')], string='Type')
    others = fields.Char('Others')
