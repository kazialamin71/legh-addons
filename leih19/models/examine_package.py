from odoo import models, fields

class ExaminePackage(models.Model):
    _name = 'examine.package'
    _description = 'ExaminePackage'

    name = fields.Char('Package name')
    price = fields.Float(string='Price')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    active = fields.Boolean('Active')
    examine_package_line_id = fields.One2many('examine.package.line', 'examine_package_id', required=True)
    total = fields.Float('Total')
