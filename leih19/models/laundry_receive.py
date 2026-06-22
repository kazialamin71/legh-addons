from odoo import models, fields

class LaundryReceive(models.Model):
    _name = 'laundry.receive'
    _description = 'LaundryReceive'

    laundry_name = fields.Many2one('laundry.laundry', string='Laundry Name', required=True)
    name = fields.Char('Cloth Type', required=True)
    color = fields.Char('Color', required=True)
    quantity = fields.Integer('Quantity', required=True)
    receive_date = fields.Date('Receive Date')
