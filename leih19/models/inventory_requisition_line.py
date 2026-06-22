from odoo import models, fields

class InventoryRequisitionLine(models.Model):
    _name = 'inventory.requisition.line'
    _description = 'InventoryRequisitionLine'

    name = fields.Char('Inventory Requisition Line Id')
    inventory_requsition_id = fields.Many2one('inventory.requisition', string='Inventory Requision ID')
    product_name = fields.Many2one('product.product', string='Product Name')
    available_qty = fields.Float('available Qty', readonly=True)
    quantity = fields.Float('Quantity')
