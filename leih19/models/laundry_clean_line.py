from odoo import models, fields

class LaundryCleanLine(models.Model):
    _name = 'laundry.clean.line'
    _description = 'LaundryCleanLine'

    laundry_clean_id = fields.Many2one('laundry.clean', string='Clean')
    linen_item = fields.Many2one('laundry.product', string='Linen Item')
    quantity = fields.Integer('Quantity')
    color = fields.Char('Color')
