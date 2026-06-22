from odoo import fields, models


class ExaminationResultAntibiogramLine(models.Model):
    _name = 'examination.result.antibiogram.line'
    _description = 'Antibiogram Result Line (R/I/S per antibiotic)'
    _order = 'sequence, id'

    result_id = fields.Many2one(
        'examination.result', string='Result', required=True, ondelete='cascade',
    )
    antibiotic_id = fields.Many2one(
        'lab.antibiotic', string='Antibiotic', required=True, ondelete='restrict',
    )
    sequence = fields.Integer(related='antibiotic_id.sequence', store=True, readonly=True)
    drug_class = fields.Char(related='antibiotic_id.drug_class', readonly=True)
    code = fields.Char(related='antibiotic_id.code', readonly=True)

    sensitivity = fields.Selection(
        [('R', 'Resistant'),
         ('I', 'Intermediate'),
         ('S', 'Sensitive')],
        string='Sensitivity',
    )
