from odoo import models, fields

class AddBill(models.Model):
    _name = 'add.bill'
    _description = 'AddBill'

    name = fields.Many2one('examination.entry', string='Test Name', required=True, ondelete='cascade')
    price = fields.Integer('Price')
    discount = fields.Integer('Discount(%)')
    total_amount = fields.Integer('Total Amount')
