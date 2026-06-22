from odoo import models, fields

class InventoryProductEntry(models.Model):
    _name = 'inventory.product.entry'
    _description = 'InventoryProductEntry'

    name = fields.Char('Entry No', readonly=True)
    invoice_no = fields.Char('Invoice/Bill No', required=True)
    invoice_date = fields.Date('Invoice/Bill Date', required=True)
    chalan_date = fields.Date('Chalan Date', required=True)
    chalan_no = fields.Char('Chalan No', required=True)
    reference_no = fields.Char('Reference No')
    total = fields.Float('Total Amount')
    partner_id = fields.Many2one('res.partner', string='Employee Name', required=True)
    grn_id = fields.Many2one('stock.picking', string='GRN NO')
    grn_journal_id = fields.Many2one('account.move', string='GRN Journal')
    advance_journal_id = fields.Many2one('account.move', string='Advance Journal')
    department = fields.Many2one('hr.department', string='Department')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse Location', required=True)
    inventory_product_entry_line_ids = fields.One2many('inventory.product.entry.line', 'inventory_product_entry_id', string='Inventory Requision Items', required=True)
    date = fields.Date('Entry Date')
    state = fields.Selection([('pending', 'Pending'), ('confirmed', 'Receive Product'), ('verify', 'Verified'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
