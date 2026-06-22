from odoo import models, fields

class CashCollection(models.Model):
    _name = 'cash.collection'
    _description = 'CashCollection'

    name = fields.Char('Cash Collection No')
    date = fields.Datetime('Date', default=None)
    type = fields.Selection([('bill', 'Bill [Diagnosis]'), ('bill_others', 'Bill [others]'), ('opd', 'OPD'), ('admission', 'Admission'), ('optics', 'Optics')], 'Type')
    total = fields.Float('Total')
    journal_id = fields.Many2one('account.move', string='Journal ')
    debit_act_id = fields.Many2one('account.account', string='Debit Account ', required=True)
    credit_act_id = fields.Many2one('account.account', string='Credit Account ', required=True)
    cash_collection_lines = fields.One2many('cash.collection.line', 'cash_collection_line_id', required=True)
    state = fields.Selection([('pending', 'Pending'), ('approve', 'Confirmed'), ('cancel', 'Cancelled')], 'State', default='pending', readonly=True)
