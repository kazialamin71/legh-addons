from odoo import models, fields

class CashCollectionLine(models.Model):
    _name = 'cash.collection.line'
    _description = 'CashCollectionLine'

    cash_collection_line_id = fields.Many2one('cash.collection', string='Cash Collection')
    mr_no = fields.Many2one('leih.money.receipt', string='MR No. ')
    opd_id = fields.Many2one('opd.ticket', string='OPD No. ')
    bill_admission_opd_id = fields.Char('Bill/Admission/OPD Number')
    amount = fields.Float('Amount')
