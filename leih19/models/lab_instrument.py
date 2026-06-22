from odoo import models, fields


class LabInstrument(models.Model):
    _name = 'lab.instrument'
    _description = 'Lab Instrument / Analyzer'
    _order = 'sequence, name'

    name = fields.Char('Instrument', required=True)
    code = fields.Char('Code')
    location = fields.Char('Location')
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Char('Description')
    active = fields.Boolean(default=True)
