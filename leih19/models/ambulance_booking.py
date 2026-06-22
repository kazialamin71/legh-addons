from odoo import models, fields

class AmbulanceBooking(models.Model):
    _name = 'ambulance.booking'
    _description = 'AmbulanceBooking'

    booking_type = fields.Char('Booking Type', required=True)
    name = fields.Char('Customer Name', required=True)
    patient_id = fields.Many2one('patient.info', string='Patient Name', required=True)
    mobile_no = fields.Char('Mobile No', required=True)
    start_from = fields.Char('Start/Pick From', required=True)
    destination = fields.Char('Destination', required=True)
    amount = fields.Float('Amount', required=True)
    advance_amount = fields.Float('Advance Amount', required=True)
    paid_amount = fields.Float('Paid Amount')
    unpaid_amount = fields.Float('Unpaid Amount')
    grace_time = fields.Float('Expected Completion Time', required=True)
    date = fields.Datetime('Booking/Request Date and Time', required=True)
    ambulance_id = fields.Many2one('ambulance.registration', string='Vehicle Name')
    state = fields.Selection([('draft', 'Pending'), ('confirm', 'Confirmed'), ('cancel', 'Cancelled')], 'Status', readonly=True, copy=False, select=True)
