from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OpdTicket(models.Model):
    _name = 'opd.ticket'
    _description = 'OpdTicket'

    name = fields.Char('Name')
    patient_name = fields.Many2one('patient.info', string='Patient Name')
    patient_id = fields.Char(related='patient_name.patient_id', string='Patient Id', readonly=True)

    # Patient details mirrored from the selected patient. They used to be plain
    # non-stored Char fields that nothing ever filled in, so the form, the list
    # and the OPD ticket printout all showed them empty.
    mobile = fields.Char(string='Mobile', compute='_compute_patient_details')
    address = fields.Char('Address', compute='_compute_patient_details')
    age = fields.Char('Age', compute='_compute_patient_details')
    sex = fields.Char('Sex', compute='_compute_patient_details')
    already_collected = fields.Boolean('Money Collected', default=False)
    date = fields.Date('Date', readonly=True, default=None)
    ref_doctors = fields.Many2one('doctors.profile', string='Reffered by')
    opd_ticket_line_id = fields.One2many('opd.ticket.line', 'opd_ticket_id', required=True)
    user_id = fields.Many2one('res.users', string='Assigned to', select=True, track_visibility='onchange')
    state = fields.Selection([('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='confirmed', readonly=True)
    total = fields.Float(string='Total')
    with_doctor_total = fields.Float(string='Total with Doctor Fee')


    prescription_count = fields.Integer(string='Prescription Count', compute='_compute_prescription_count')

    @api.depends('patient_name')
    def _compute_patient_details(self):
        sex_labels = dict(self.env['patient.info']._fields['sex'].selection)
        for rec in self:
            patient = rec.patient_name
            rec.mobile = patient.mobile or False
            rec.address = patient.address or False
            rec.age = patient.age or False
            rec.sex = sex_labels.get(patient.sex, patient.sex) or False

    def _compute_prescription_count(self):
        Prescription = self.env['doctor.prescription']
        for rec in self:
            rec.prescription_count = Prescription.search_count([('opd_ticket_id', '=', rec.id)])

    def action_create_prescription(self):
        self.ensure_one()
        if not self.patient_name:
            raise UserError(_('Please select a patient first.'))
        if not self.ref_doctors:
            raise UserError(_('Please select a doctor first.'))
        prescription = self.env['doctor.prescription'].create({
            'patient_id': self.patient_name.id,
            'doctor_id': self.ref_doctors.id,
            'department': self.opd_ticket_line_id[:1].department or self.ref_doctors.department,
            'source_model': 'opd.ticket',
            'opd_ticket_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescription'),
            'res_model': 'doctor.prescription',
            'view_mode': 'form',
            'res_id': prescription.id,
            'target': 'current',
        }

    def action_view_prescriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescriptions'),
            'res_model': 'doctor.prescription',
            'view_mode': 'list,form',
            'domain': [('opd_ticket_id', '=', self.id)],
            'context': {
                'default_patient_id': self.patient_name.id,
                'default_doctor_id': self.ref_doctors.id,
                'default_opd_ticket_id': self.id,
                'default_source_model': 'opd.ticket',
            },
        }
