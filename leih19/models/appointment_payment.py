from odoo import models, fields

class AppointmentPayment(models.Model):
    _name = 'appointment.payment'
    _description = 'AppointmentPayment'

    cal_st_date = fields.Date('Calculation Start Date')
    cal_end_date = fields.Date('Calculation End Date')
    ref_doctors = fields.Many2one('doctors.profile', string='Doctor Name')
    total_payable_amount = fields.Float('Total Payable Amount')
    appointment_payment_line_ids = fields.One2many('appointment.payment.line', 'appointment_payment_line_ids')
