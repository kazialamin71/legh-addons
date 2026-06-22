from odoo import models, fields

class AdmissionPaymentConfiguration(models.Model):
    _name = 'admission.payment.configuration'
    _description = 'AdmissionPaymentConfiguration'

    name = fields.Char('Name')
    doctor_id = fields.Many2one('doctors.profile', string='Doctor/Broker Name')
    start_date = fields.Date('MOU Start Date')
    end_date = fields.Date('MOU End Date')
    overall_admission_rate = fields.Float('Overall admission Rate (%)')
    overall_default_discount = fields.Float('Overall Discount Rate (%)')
    max_default_discount = fields.Float('Max Discount Rate (%)')
    deduct_from_discount = fields.Boolean('Deduct Excess Discount From admission')
    add_few_departments = fields.Boolean('Add by Department')
    department_ids = fields.Many2one('diagnosis.department', string='Department List')
    admission_configuration_line_ids = fields.One2many('admission.payment.configuration.line', 'admission_configuration_line_ids')
    state = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)
