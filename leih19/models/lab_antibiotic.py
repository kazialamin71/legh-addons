from odoo import models, fields


class LabAntibiotic(models.Model):
    _name = 'lab.antibiotic'
    _description = 'Antibiotic (for antibiogram)'
    _order = 'sequence, name'

    name = fields.Char('Antibiotic', required=True)
    code = fields.Char('Code')
    drug_class = fields.Char('Class')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
