from odoo import models, fields

class AdvanceCash(models.Model):
    _name = 'advance.cash'
    _description = 'AdvanceCash'

    date = fields.Date('Date')
    name = fields.Char('Cash No.')
    purpose = fields.Char('Purpose', required=True)
    amount = fields.Float('Amount', required=True)
    journal_id = fields.Many2one('account.move', string='Journal ')
    credit_accounts = fields.Many2one('account.account', string='Cash/Bank Account')
    debit_accounts = fields.Many2one('account.account', string='Advance Account')
    partner_id = fields.Many2one('res.partner', string='Partner Name', required=True)
    state = fields.Selection([('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
