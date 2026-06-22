from odoo import models, fields

class OpticsLensSaleLine(models.Model):
    _name = 'optics.lens.sale.line'
    _description = 'OpticsLensSaleLine'

    name = fields.Many2one('product.lens', string='Lens Name', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Lens Name')
    optics_sale_id = fields.Many2one('optics.sale', string='Information')
    price = fields.Integer('Unit Price')
    qty = fields.Integer('Quantity')
    total_amount = fields.Integer('Total Amount')
