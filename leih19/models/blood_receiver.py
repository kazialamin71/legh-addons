from odoo import models, fields

class BloodReceiver(models.Model):
    _name = 'blood.receiver'
    _description = 'BloodReceiver'

    name = fields.Char('Name')
    buyer_name = fields.Char('Buyer Name', required=True)
    receive_date = fields.Date('Date', required=True)
    mobile_no = fields.Char('Mobile No', required=True)
    patient_id = fields.Many2one('patient.info', string='Patient Name')
    description = fields.Text('Description')
    blood_group = fields.Char('Blood Group')
    price = fields.Float('Price')
    paid_amount = fields.Float('Paid Amount')
    unpaid_amount = fields.Float('Unpaid Amount')
