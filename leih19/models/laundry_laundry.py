from odoo import models, fields

class LaundryLaundry(models.Model):
    _name = 'laundry.laundry'
    _description = 'LaundryLaundry'

    name = fields.Char('Name', required=True)
    address = fields.Char('Address', required=True)
