from odoo import models, fields


class ExaminationPossibleValue(models.Model):
    _name = 'examination.possible.value'
    _description = 'Possible Result Value (e.g. Positive / Negative)'
    _order = 'sequence, id'

    name = fields.Char('Value', required=True)
    sequence = fields.Integer('Sequence', default=10)
    examination_line_id = fields.Many2one(
        'examination.entry.line', string='Component', ondelete='cascade',
    )
    is_default = fields.Boolean('Default')
