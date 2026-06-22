from odoo import models, fields
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
from num2words import num2words

class DoctorProfileAdmissionLine(models.Model):
    _name = "doctor.profile.admission.line"
    _description = "Doctor Profile Admission Line"

    name = fields.Char(string="Name")
    doctor_profile_id = fields.Many2one("doctors.profile", string="Doctor Name")
    hospital_doctor_line_item = fields.Many2one("hospital.admission", string="Doctor Info")
    doctor_visit_qty = fields.Float(string="Visit Times", default=1.0)
    visit_fee = fields.Float(string="Visit Fee")
    total_amount = fields.Float(string="Total Amount")

    @api.onchange("doctor_profile_id")
    def _onchange_doctor(self):
        for rec in self:
            if rec.doctor_profile_id:
                rec.doctor_visit_qty = 1
                rec.visit_fee = rec.doctor_profile_id.ipd_visit
                rec.total_amount = rec.doctor_profile_id.ipd_visit

    @api.onchange("visit_fee", "doctor_visit_qty")
    def _onchange_total(self):
        for rec in self:
            rec.total_amount = rec.visit_fee * rec.doctor_visit_qty
