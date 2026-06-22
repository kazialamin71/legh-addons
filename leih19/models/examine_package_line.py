from odoo import models, fields

class ExaminePackageLine(models.Model):
    _name = 'examine.package.line'
    _description = 'ExaminePackageLine'

    name = fields.Many2one('examination.entry', string='Test Name', required=True, ondelete='cascade')
    examine_package_id = fields.Many2one('examine.package', string='Information')
    price = fields.Integer('Price')
    discount = fields.Integer('Discount')
    total_amount = fields.Integer('Total Amount')
