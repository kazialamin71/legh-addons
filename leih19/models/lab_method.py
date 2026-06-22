from odoo import models, fields


class LabMethod(models.Model):
    _name = 'lab.method'
    _description = 'Lab Test Method'
    _order = 'sequence, name'

    name = fields.Char('Method', required=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Char('Description')
    active = fields.Boolean(default=True)
