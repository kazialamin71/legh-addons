from odoo import models, fields

class CcCollection(models.Model):
    _name = 'cc.collection'
    _description = 'CcCollection'

    date_start = fields.Datetime('Date Start', required=True)
    date_end = fields.Datetime('Date End', required=True)
