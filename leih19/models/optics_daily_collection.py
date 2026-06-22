from odoo import models, fields

class OpticsDailyCollection(models.Model):
    _name = 'optics.daily.collection'
    _description = 'OpticsDailyCollection'

    date_start = fields.Datetime('Date', required=True)
    date_end = fields.Datetime('Date End', required=True)
