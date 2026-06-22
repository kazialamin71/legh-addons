from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
from num2words import num2words

class HospitalBedLine(models.Model):
    _name = "hospital.bed.line"
    _description = "Hospital Bed Line"

    hospital_bed_item_id = fields.Many2one("hospital.admission", string="Bed Item")
    bed_no = fields.Many2one("hospital.bed", string="Bed Name", ondelete="cascade")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    bed_qty = fields.Float(string="Bed Quantity", default=1.0)
    perday_charge = fields.Float(string="Per Day Charge")
    total_amount = fields.Float(string="Total Amount")

    @api.onchange("bed_no")
    def _onchange_bed(self):
        for rec in self:
            if rec.bed_no:
                rec.bed_qty = 1
                rec.perday_charge = rec.bed_no.perday_charge
                rec.total_amount = rec.bed_no.perday_charge

    @api.onchange("bed_qty", "perday_charge")
    def _onchange_bed_qty(self):
        for rec in self:
            rec.total_amount = rec.perday_charge * rec.bed_qty