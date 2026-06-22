from odoo import models, fields

class DiscountLine(models.Model):
    _name = 'discount.line'
    _description = 'DiscountLine'

    category = fields.Many2one('discount.category', string='Discount Category')
    ref = fields.Char('Reference')
    accounts = fields.Many2one('account.account', string='Account Name')
    fixed_amount = fields.Integer('Amount(fixed)')
    percent_amount = fields.Integer('Amount(%)')
    discount_id = fields.Many2one('discount', string='discount Id')
