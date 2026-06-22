from odoo import models, fields

class CommissionPayment(models.Model):
    _name = 'commission.payment'
    _description = 'CommissionPayment'

    name = fields.Char('CP No.')
    doctor_id = fields.Many2one('doctors.profile', string='Name')
    date = fields.Date('Payment Date')
    cc_id = fields.Many2one('commission', string='Commission')
    debit_id = fields.Many2one('account.account', string='Debit Account')
    credit_id = fields.Many2one('account.account', string='Credit Account')
    paid_amount = fields.Float('Paid Amount')
    due_amount = fields.Float('Due Amount')
    period_id = fields.Char('Period')
    journal_id = fields.Many2one('account.move', string='Journal')
    note = fields.Text('Note')
    state = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
