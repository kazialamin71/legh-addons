from odoo import models, fields


class ExaminationReportTemplate(models.Model):
    _name = 'examination.report.template'
    _description = 'Examination Report Template (descriptive)'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    report_type = fields.Selection(
        [('radiology', 'Radiology'),
         ('descriptive', 'Descriptive (USG/Echo/etc.)'),
         ('pathology', 'Pathology'),
         ('other', 'Other')],
        string='Report Type', default='descriptive', required=True,
    )
    body_html = fields.Html('Body', sanitize=False)
    department = fields.Many2one('diagnosis.department', string='Department')
    examination_entry_ids = fields.Many2many(
        'examination.entry', 'examination_entry_template_rel',
        'template_id', 'examination_entry_id',
        string='Applies to Tests',
    )
    active = fields.Boolean(default=True)
    note = fields.Char('Note')
