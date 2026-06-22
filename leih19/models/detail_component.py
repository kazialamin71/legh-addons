from odoo import models, fields

class DetailComponent(models.Model):
    _name = 'detail.component'
    _description = 'DetailComponent'

    date_start = fields.Datetime('Date Start', required=True)
    date_end = fields.Datetime('Date End', required=True)
