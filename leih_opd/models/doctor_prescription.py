from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DoctorPrescription(models.Model):
    _inherit = 'doctor.prescription'

    template_id = fields.Many2one('prescription.template', string='Template')

    def action_print_prescription(self):
        """Override: the base method referenced a non-existent report id
        ('leis_migrated_models.*'); point at the corrected action."""
        self.ensure_one()
        return self.env.ref(
            'leih19.action_report_doctor_prescription').report_action(self)

    def action_apply_template(self):
        """Append the chosen template's lines and fill empty header notes."""
        self.ensure_one()
        tmpl = self.template_id
        if not tmpl:
            raise UserError(_('Please select a template first.'))

        header = {}
        if tmpl.chief_complaint and not self.chief_complaint:
            header['chief_complaint'] = tmpl.chief_complaint
        if tmpl.diagnosis and not self.diagnosis:
            header['diagnosis'] = tmpl.diagnosis
        if tmpl.note and not self.note:
            header['note'] = tmpl.note
        if not self.department and tmpl.department:
            header['department'] = tmpl.department
        if header:
            self.write(header)

        self.medicine_line_ids = [(0, 0, {
            'product_id': line.product_id.id,
            'medicine_name': line.medicine_name,
            'dosage': line.dosage,
            'frequency': line.frequency,
            'duration': line.duration,
            'instruction': line.instruction,
        }) for line in tmpl.medicine_line_ids]
        self.advice_line_ids = [(0, 0, {
            'advice': line.advice,
        }) for line in tmpl.advice_line_ids]
        self.test_line_ids = [(0, 0, {
            'examination_id': line.examination_id.id,
            'test_name': line.test_name,
            'note': line.note,
        }) for line in tmpl.test_line_ids]
        return True


class DoctorPrescriptionMedicine(models.Model):
    _inherit = 'doctor.prescription.medicine'

    product_id = fields.Many2one(
        'product.product', string='Medicine Item',
        help='Stock/POS product, so the pharmacy can dispense it directly.')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.medicine_name = self.product_id.name


class DoctorPrescriptionTest(models.Model):
    _inherit = 'doctor.prescription.test'

    examination_id = fields.Many2one(
        'examination.entry', string='Investigation Item',
        help='Billing item, so the desk can load it straight into a bill.')

    @api.onchange('examination_id')
    def _onchange_examination_id(self):
        if self.examination_id:
            self.test_name = self.examination_id.name
