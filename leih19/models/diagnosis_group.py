from odoo import models, fields

class DiagnosisGroup(models.Model):
    _name = 'diagnosis.group'
    _description = 'Diagnosis Group'

    name = fields.Char('Group Name', required=True)
    department = fields.Many2one('diagnosis.department', string='Department')
    year = fields.Integer('Year')
