from odoo import models, fields

class InvestigationPaymentLine(models.Model):
    _name = 'investigation.payment.line'
    _description = 'InvestigationPaymentLine'

    investigation_payment_line_ids = fields.Many2one('investigation.payment', string='Admission Payment')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    name = fields.Many2one('examination.entry', string='Test Name')
    discount_amount = fields.Float('Discount Amount')
    test_amount = fields.Float('Test Amount')
    mou_payable_comm_var = fields.Float('MOU Payable Amount (%)')
    mou_payable_comm_fixed = fields.Float('MOU Payable Fixed')
    mou_payable_comm_max_cap = fields.Float('MOU Max CAP Amount')
    after_discount = fields.Float('After Discount Amount')
    payable_amount = fields.Float('Payable Amount')
