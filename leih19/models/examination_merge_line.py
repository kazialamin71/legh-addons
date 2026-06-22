from odoo import models, fields

class ExaminationMergeLine(models.Model):
    _name = 'examination.merge.line'
    _description = 'Examination Merge Line'

    merge_id = fields.Many2many('examination.entry', string='Test Entry')
    examinationentry_id = fields.Many2one('examination.entry', string='Merged Test Entry')
