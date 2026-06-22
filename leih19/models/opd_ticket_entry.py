from odoo import models, fields

class OpdTicketEntry(models.Model):
    _name = 'opd.ticket.entry'
    _description = 'OpdTicketEntry'

    name = fields.Char('Name')
    department = fields.Many2one('diagnosis.department', string='Department')
    fee = fields.Float('Fee')
    accounts_id = fields.Many2one('account.account', string='Account ID', required=True)
    total_cash = fields.Float('Total Cash')
