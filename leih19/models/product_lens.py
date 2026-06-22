from odoo import models, fields

class ProductLens(models.Model):
    _name = 'product.lens'
    _description = 'ProductLens'

    lens_code = fields.Char('Code')
    name = fields.Char('Name')
    purchase_price = fields.Float('Purchase price')
    sell_price = fields.Float('Sale Price')
    lens_type = fields.Selection([('glass', 'Glass'), ('plastic', 'Plastic')], default='plastic')
    supplier = fields.Char('Supplier Name')
