from odoo import models, fields

class AppointmentPaymentLine(models.Model):
    _name = 'appointment.payment.line'
    _description = 'AppointmentPaymentLine'

    appointment_payment_line_ids = fields.Many2one('appointment.payment', string='Admission Payment')
    appointment_booking_id = fields.Char('Appointment ID')
    patient_name = fields.Char('Patient Name')
    patient_status = fields.Char('Patient Status')
    date = fields.Date(string='Date')
    amount = fields.Float('Amount')
