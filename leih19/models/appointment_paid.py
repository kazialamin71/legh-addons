from odoo import models, fields

class AppointmentPaid(models.Model):
    _name = 'appointment.paid'
    _description = 'AppointmentPaid'

    patient_status = fields.Selection([('new', 'New Patient'), ('review', 'Review')], string='Patient Status')
    amount = fields.Float('amount')
