from odoo import fields, models


class StockQuant(models.Model):
    """Supplier and generic carried onto the quant so stock can be read by either.

    Stored and indexed rather than computed on the fly, because the only useful
    thing to do with them is group and filter a warehouse's whole stock by them,
    and a non-stored related field can do neither.
    """
    _inherit = 'stock.quant'

    supplier_id = fields.Many2one(
        related='product_id.product_tmpl_id.supplier_id', string='Supplier',
        store=True, index=True, readonly=True)
    medicine_generic_id = fields.Many2one(
        related='product_id.product_tmpl_id.medicine_generic_id',
        string='Generic (Molecule)', store=True, index=True, readonly=True)
