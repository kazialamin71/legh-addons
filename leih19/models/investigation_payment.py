from odoo import models, fields

class InvestigationPayment(models.Model):
    _name = 'investigation.payment'
    _description = 'InvestigationPayment'

    cal_st_date = fields.Datetime('Calculation Start Date')
    cal_end_date = fields.Datetime('Calculation End Date')
    ref_doctors = fields.Many2one('doctors.profile', string='Doctor Name')
    investigation_payment_line_ids = fields.One2many('investigation.payment.line', 'investigation_payment_line_ids')
    given_discount_amount = fields.Float('Total Discount')
    total_amount = fields.Float('Total Payable Amount')
    total_bill = fields.Float('Total Billing Amount')
    total_tests = fields.Float('Total Tests in All Billing')
    paid_amount = fields.Float('Paid Amount')
    state = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('paid', 'Paid & Close'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
