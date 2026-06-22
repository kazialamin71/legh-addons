from odoo import models, fields

class BloodDonar(models.Model):
    _name = 'blood.donar'
    _description = 'BloodDonar'

    name = fields.Char('Name')
    doner_name = fields.Char('Donar Name', required=True)
    mobile_no = fields.Char('Mobile No', required=True)
    date = fields.Date('Received Date', required=True)
    receive_date = fields.Date('Received Date')
    description = fields.Text('Description')
    group = fields.Char('Blood Group')
    cost = fields.Float('Cost')
    active = fields.Boolean('Expired')
    donated = fields.Boolean('donated')
