from odoo import api, fields, models


class DoctorProfileAdmissionLine(models.Model):
    _name = "doctor.profile.admission.line"
    _description = "Doctor Profile Admission Line"
    _order = "visit_datetime desc, id desc"

    name = fields.Char(string="Note")
    doctor_profile_id = fields.Many2one("doctors.profile", string="Doctor Name")
    hospital_doctor_line_item = fields.Many2one("hospital.admission", string="Doctor Info")
    visit_datetime = fields.Datetime(string="Date & Time", default=fields.Datetime.now)
    doctor_visit_qty = fields.Float(string="Visit Times", default=1.0)
    # The fee is pre-filled from the doctor's IPD visit rate but stays editable
    # for the odd visit that is billed differently.
    visit_fee = fields.Float(
        string="Visit Fee", compute="_compute_visit_fee", store=True, readonly=False)
    # Derived, so the admission total is right even when a line is created from
    # code or an import, where onchanges never run.
    total_amount = fields.Float(
        string="Total Amount", compute="_compute_total_amount", store=True)

    @api.depends("doctor_profile_id")
    def _compute_visit_fee(self):
        for rec in self:
            if rec.doctor_profile_id:
                rec.visit_fee = rec.doctor_profile_id.ipd_visit
            else:
                rec.visit_fee = rec.visit_fee or 0.0

    @api.depends("visit_fee", "doctor_visit_qty")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.visit_fee * (rec.doctor_visit_qty or 1.0)
