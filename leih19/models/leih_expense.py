from odoo import models, fields

class LeihExpense(models.Model):
    _name = 'leih.expense'
    _description = 'LeihExpense'

    expense_type = fields.Selection([('internal', 'Internal'), ('external', 'External'), ('convinent', 'Convinent'), ('entertainment', 'Entertainment')], string='Expense Type')
    ex_name = fields.Char('Expense Name')
    amount = fields.Float('Amount', required=True)
    responsible_person = fields.Char('Responsible Person')
    date = fields.Date('Date')
    description = fields.Text('Description')
    state = fields.Selection([('pending', 'Pending'), ('approved', 'Approved'), ('canceled', 'Canceled')], 'Status', default='pending', required=True, readonly=True, copy=False)
