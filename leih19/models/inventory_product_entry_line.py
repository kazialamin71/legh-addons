from odoo import models, fields

class InventoryProductEntryLine(models.Model):
    _name = 'inventory.product.entry.line'
    _description = 'InventoryProductEntryLine'

    name = fields.Char('Inventory Requisition Line Id')
    inventory_product_entry_id = fields.Many2one('inventory.product.entry', string='Inventory Entry ID')
    product_name = fields.Many2one('product.product', string='Product Name')
    account_id = fields.Many2one('account.account', string='Account')
    quantity = fields.Float('Quantity')
    unit_price = fields.Float('Unit Price')
    total_price = fields.Float('Total Price')
