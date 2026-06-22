from odoo import models, fields

class AdmissionPaymentConfigurationLine(models.Model):
    _name = 'admission.payment.configuration.line'
    _description = 'AdmissionPaymentConfigurationLine'

    name = fields.Char('name')
    admission_configuration_line_ids = fields.Many2one('admission.payment.configuration', string='admission Configuration ID')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    test_id = fields.Many2one('examination.entry', string='Test Name')
    applicable = fields.Boolean('Applicable')
    fixed_amount = fields.Float('Fixed Amount')
    variance_amount = fields.Float('Amount (%)')
    test_price = fields.Float('Test Fee')
    est_admission_amount = fields.Float('admission Amount')
    max_admission_amount = fields.Float('Max admission Amount')
