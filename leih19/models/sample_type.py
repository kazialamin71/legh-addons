from odoo import models, fields

class SampleType(models.Model):
    _name = 'sample.type'
    _description = 'SampleType'

    name = fields.Char('Sample Type', required=True)
