from odoo import models, fields

class AppointmentBooking(models.Model):
    _name = 'appointment.booking'
    _description = 'AppointmentBooking'

    name = fields.Char('Appointment')
    patient_name = fields.Char('Patient Name', required=True)
    age = fields.Char('Age', required=True)
    sex = fields.Char('Sex')
    phone = fields.Char('Mobile No.')
    address = fields.Char('Address')
    doctor_name = fields.Many2one('doctors.profile', string='Doctor Name')
    time = fields.Char('Time')
    date = fields.Date('Date')
    status = fields.Selection([('pending', 'Pending'), ('reached', 'Reached'), ('paid', 'Paid')], string='Status', default='pending')
    patient_status = fields.Selection([('new', 'New Patient'), ('review', 'Review')], string='Patient Status')
    amount = fields.Float('amount')
    payment_done = fields.Boolean('Payment', default=False)
