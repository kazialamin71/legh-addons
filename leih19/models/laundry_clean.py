from odoo import models, fields

class LaundryClean(models.Model):
    _name = 'laundry.clean'
    _description = 'LaundryClean'

    name = fields.Char('Name', required=True)
    send_date = fields.Date('Send Date')
    laundry_name = fields.Many2one('laundry.laundry', string='Laundry Name', required=True)
    back_date = fields.Date('Delivered Date')
    state = fields.Selection([('store', 'Store'), ('sent to laundry', 'Sent to Laundry'), ('received', 'Received'), ('cancelled', 'Cancelled')], 'Status', default='sent to laundry', required=True, readonly=True, copy=False)
    product_line = fields.One2many('laundry.clean.line', 'laundry_clean_id')
