from odoo import models, fields

class CommissionCalculationLine(models.Model):
    _name = 'commission.calculation.line'
    _description = 'CommissionCalculationLine'

    commission_calculation_line_ids = fields.Many2one('commission.calculation', string='Commission calculation ID')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    test_id = fields.Many2one('examination.entry', string='Test Name')
    discount_amount = fields.Float('Discount Amount')
    test_amount = fields.Float('Test Amount')
    mou_payable_commission_var = fields.Float('MOU Payable Commission (%)')
    mou_payable_commission = fields.Float('MOU Payable Commission Fixed')
    payble_amount = fields.Float('Payable Amount')
    after_discount_amount = fields.Float('After Discount Amount')
    mou_max_cap = fields.Float('MOU Max Cap Amount')
