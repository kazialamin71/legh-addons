from odoo import models, fields

class DiscountConfigurationLine(models.Model):
    _name = 'discount.configuration.line'
    _description = 'DiscountConfigurationLine'

    discount_donfiguration_line_ids = fields.Many2one('discount.configuration', string='Discount configuration Id')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    test_id = fields.Many2one('examination.entry', string='Test Name')
    test_price = fields.Float('Test Fee')
    applicable = fields.Boolean('Applicable')
    fixed_amount = fields.Float('Fixed Amount')
    variance_amount = fields.Float('Amount (%)')
    after_discount = fields.Float('After Discount Amount')
