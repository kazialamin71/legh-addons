from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DoctorPrescription(models.Model):
    _name = 'doctor.prescription'
    _description = 'Doctor Prescription'
    _order = 'id desc'

    name = fields.Char(string='Prescription No', default='New', copy=False, readonly=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    patient_id = fields.Many2one('patient.info', string='Patient', required=True)
    patient_code = fields.Char(related='patient_id.patient_id', string='Patient ID', store=True, readonly=True)
    age = fields.Char(related='patient_id.age', string='Age', readonly=True)
    sex = fields.Selection(related='patient_id.sex', string='Sex', readonly=True)
    mobile = fields.Char(related='patient_id.mobile', string='Mobile', readonly=True)
    address = fields.Char(related='patient_id.address', string='Address', readonly=True)
    doctor_id = fields.Many2one('doctors.profile', string='Doctor', required=True)
    department = fields.Char(string='Department')
    template_id = fields.Many2one('prescription.template', string='Template')
    source_model = fields.Selection([
        ('opd.ticket', 'OPD Ticket'),
        ('hospital.admission', 'Hospital Admission'),
    ], string='Source Document', readonly=True)
    opd_ticket_id = fields.Many2one('opd.ticket', string='OPD Ticket', readonly=True)
    admission_id = fields.Many2one('hospital.admission', string='Admission', readonly=True)
    chief_complaint = fields.Text(string='Chief Complaint')
    diagnosis = fields.Text(string='Diagnosis')
    note = fields.Text(string='Doctor Note')
    followup_date = fields.Date(string='Follow Up Date')
    followup_note = fields.Char(string='Follow Up Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    medicine_line_ids = fields.One2many('doctor.prescription.medicine', 'prescription_id', string='Medicines')
    advice_line_ids = fields.One2many('doctor.prescription.advice', 'prescription_id', string='Advices')
    test_line_ids = fields.One2many('doctor.prescription.test', 'prescription_id', string='Tests')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('doctor.prescription') or 'New'
            if not vals.get('department') and vals.get('doctor_id'):
                doctor = self.env['doctors.profile'].browse(vals['doctor_id'])
                vals['department'] = doctor.department
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'done'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_print_prescription(self):
        self.ensure_one()
        return self.env.ref(
            'leih_opd.action_report_doctor_prescription').report_action(self)

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
    _name = 'doctor.prescription.medicine'
    _description = 'Doctor Prescription Medicine'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    prescription_id = fields.Many2one('doctor.prescription', string='Prescription', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Medicine Item',
        help='Stock/POS product, so the pharmacy can dispense it directly.')
    medicine_name = fields.Char(string='Medicine', required=True)
    dosage = fields.Char(string='Dosage')
    before_eat = fields.Boolean(string='Before Eat')
    frequency = fields.Char(string='Frequency')
    duration = fields.Char(string='Duration')
    instruction = fields.Char(string='Instruction')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.medicine_name = self.product_id.name


class DoctorPrescriptionAdvice(models.Model):
    _name = 'doctor.prescription.advice'
    _description = 'Doctor Prescription Advice'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    prescription_id = fields.Many2one('doctor.prescription', string='Prescription', required=True, ondelete='cascade')
    advice = fields.Char(string='Advice', required=True)


class DoctorPrescriptionTest(models.Model):
    _name = 'doctor.prescription.test'
    _description = 'Doctor Prescription Test'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    prescription_id = fields.Many2one('doctor.prescription', string='Prescription', required=True, ondelete='cascade')
    examination_id = fields.Many2one(
        'examination.entry', string='Investigation Item',
        help='Billing item, so the desk can load it straight into a bill.')
    test_name = fields.Char(string='Test', required=True)
    note = fields.Char(string='Note')

    @api.onchange('examination_id')
    def _onchange_examination_id(self):
        if self.examination_id:
            self.test_name = self.examination_id.name
