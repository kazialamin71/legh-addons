from odoo import models, fields


class TubeColor(models.Model):
    _name = 'tube.color'
    _description = 'Tube Color (sample collection grouping)'
    _order = 'sequence, name'

    name = fields.Char('Tube Color', required=True)
    code = fields.Char('HEX Color', help='e.g. #FFFF00 for yellow tube')
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Char('Description')
    active = fields.Boolean(default=True)
