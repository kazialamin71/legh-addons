from odoo import models, fields

class DiscountCategory(models.Model):
    _name = 'discount.category'
    _description = 'DiscountCategory'

    name = fields.Char('Discount Type')
    parent = fields.Many2one('discount.category', string='Parent Category')
    account_id = fields.Many2one('account.account', string='Accounts')
