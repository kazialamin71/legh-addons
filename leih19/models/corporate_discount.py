from odoo import models, fields

class CorporateDiscount(models.Model):
    _name = 'corporate.discount'
    _description = 'CorporateDiscount'

    name = fields.Char('Corporate Disocunt ID')
    bill_id = fields.Many2one('bill.register', string='Bill ID')
    date = fields.Date('Date')
    corporate_id = fields.Many2one('discount.configuration', string='Corporate ID')
    discount_amount = fields.Float('Discount Amount')
    total_amount = fields.Float('Due Amount')
    period_id = fields.Char('Period')
    journal_id = fields.Many2one('account.move', string='Journal')
    note = fields.Text('Note')
    state = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
