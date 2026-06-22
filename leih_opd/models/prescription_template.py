from odoo import api, fields, models


class PrescriptionTemplate(models.Model):
    """A reusable prescription preset a doctor can apply with one click."""
    _name = 'prescription.template'
    _description = 'Prescription Template'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    doctor_id = fields.Many2one('doctors.profile', string='Doctor')
    department = fields.Char('Department')
    active = fields.Boolean(default=True)
    chief_complaint = fields.Text('Chief Complaint')
    diagnosis = fields.Text('Diagnosis')
    note = fields.Text('Doctor Note')

    medicine_line_ids = fields.One2many(
        'prescription.template.medicine', 'template_id', string='Medicines')
    advice_line_ids = fields.One2many(
        'prescription.template.advice', 'template_id', string='Advices')
    test_line_ids = fields.One2many(
        'prescription.template.test', 'template_id', string='Investigations')


class PrescriptionTemplateMedicine(models.Model):
    _name = 'prescription.template.medicine'
    _description = 'Prescription Template Medicine'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'prescription.template', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Medicine Item')
    medicine_name = fields.Char('Medicine', required=True)
    dosage = fields.Char('Dosage')
    frequency = fields.Char('Frequency')
    duration = fields.Char('Duration')
    instruction = fields.Char('Instruction')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.medicine_name = self.product_id.name


class PrescriptionTemplateAdvice(models.Model):
    _name = 'prescription.template.advice'
    _description = 'Prescription Template Advice'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'prescription.template', required=True, ondelete='cascade')
    advice = fields.Char('Advice', required=True)


class PrescriptionTemplateTest(models.Model):
    _name = 'prescription.template.test'
    _description = 'Prescription Template Investigation'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'prescription.template', required=True, ondelete='cascade')
    examination_id = fields.Many2one('examination.entry', string='Investigation Item')
    test_name = fields.Char('Investigation', required=True)
    note = fields.Char('Note')

    @api.onchange('examination_id')
    def _onchange_examination_id(self):
        if self.examination_id:
            self.test_name = self.examination_id.name
