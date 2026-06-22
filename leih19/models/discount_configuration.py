from odoo import models, fields

class DiscountConfiguration(models.Model):
    _name = 'discount.configuration'
    _description = 'DiscountConfiguration'

    name = fields.Char('Client Name')
    type = fields.Selection([('fixed', 'Fixed'), ('variance', 'Variance')], 'Type')
    overall_discount = fields.Float('Overall Discount Amount(%)')
    department = fields.Many2one('diagnosis.department', string='Department')
    from_date = fields.Date('From (Date)')
    to_date = fields.Date('To (Date)')
    discount_donfiguration_line_ids = fields.One2many('discount.configuration.line', 'discount_donfiguration_line_ids')
