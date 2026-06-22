from odoo import models, fields

class CommissionCalculation(models.Model):
    _name = 'commission.calculation'
    _description = 'CommissionCalculation'

    name = fields.Char('Name')
    doctor_id = fields.Many2one('doctors.profile', string='Doctor/Broker Name')
    start_date = fields.Date('Calculation Start Date')
    end_date = fields.Date('Calculation End Date')
    total_commission_amount = fields.Float('Total Commission Amount')
    given_discount_amount = fields.Float('Total Discount Amount')
    total_paybale_amount = fields.Float('Total Payable Amount')
    no_of_total_patient = fields.Float('Total Patients')
    no_of_total_bill = fields.Float('Total Bill')
    no_of_total_bill_amount = fields.Float('Total Bill Amount')
    no_of_total_test = fields.Float('Total Test')
    commission_calculation_line_ids = fields.One2many('commission.calculation.line', 'commission_calculation_line_ids')
    status = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('cancelled', 'Cancelled'), ('close', 'Closed')], 'Status', default='pending', readonly=True)
    state = fields.Selection([('pending', 'Unpaid'), ('partially_paid', 'Partially Paid'), ('paid', 'Paid')], 'State', default='pending', readonly=True)
