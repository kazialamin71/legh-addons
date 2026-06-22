from odoo import models, fields

class InventoryRequisition(models.Model):
    _name = 'inventory.requisition'
    _description = 'InventoryRequisition'

    name = fields.Char('Inventory Requisition')
    reference_no = fields.Char('Reference No')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse Location', required=True)
    partner_id = fields.Many2one('res.partner', string='Receiver')
    challan_id = fields.Many2one('stock.picking', string='Challan NO')
    expense_journal_id = fields.Many2one('account.move', string='Expense Journal')
    department = fields.Many2one('hr.department', string='Department', required=True)
    inventory_requisition_line_ids = fields.One2many('inventory.requisition.line', 'inventory_requsition_id', string='Inventory Requision Items', required=True)
    date = fields.Date('Date')
    state = fields.Selection([('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
