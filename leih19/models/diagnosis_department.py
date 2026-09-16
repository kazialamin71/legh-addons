from odoo import models, fields

class DiagnosisDepartment(models.Model):
    _name = 'diagnosis.department'
    _description = 'Diagnosis Department'

    name = fields.Char('Department Name', required=True)
    parent = fields.Many2one('diagnosis.department', string='Parent')
    modality = fields.Selection(
        [('pathology', 'Pathology'),
         ('radiology', 'Radiology (X-ray / CT / MRI)'),
         ('usg', 'USG / Imaging'),
         ('other', 'Other')],
        string='Lab Modality', default='pathology',
        help='Controls which lab staff can see results from this department. '
             'A user only sees results whose department modality matches a lab '
             'group they belong to.')
    signatory_id = fields.Many2one(
        'doctors.profile', string='Report Signatory (Pathologist)',
        help='Pathologist / consultant whose name, degree and designation print as the '
             'authorizing signature on lab reports for this department.',
    )
    report_disclaimer_html = fields.Html(
        'Report Disclaimer (override)', sanitize=False,
        help='Disclaimer printed on this department\'s lab reports. Leave empty '
             'to use the company-wide disclaimer.',
    )
