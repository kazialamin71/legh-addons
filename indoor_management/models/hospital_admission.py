from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HospitalAdmission(models.Model):
    _inherit = "hospital.admission"

    current_bed_line_id = fields.Many2one(
        "hospital.bed.line",
        string="Current Bed Line",
        compute="_compute_current_bed",
        store=False,
    )
    current_bed_id = fields.Many2one(
        "hospital.bed",
        string="Current Bed",
        compute="_compute_current_bed",
        store=False,
    )
    current_ward_id = fields.Many2one(
        "hospital.ward",
        string="Current Ward",
        compute="_compute_current_bed",
        store=False,
    )
    current_category_id = fields.Many2one(
        "bed.category",
        string="Current Category",
        compute="_compute_current_bed",
        store=False,
    )
    bed_line_count = fields.Integer(
        string="Accommodation Entries",
        compute="_compute_bed_line_count",
    )

    @api.depends("hospital_bed_line_id", "hospital_bed_line_id.end_date")
    def _compute_current_bed(self):
        for rec in self:
            open_lines = rec.hospital_bed_line_id.filtered(lambda l: not l.end_date)
            line = open_lines.sorted("start_date", reverse=True)[:1]
            rec.current_bed_line_id = line.id if line else False
            rec.current_bed_id = line.bed_no.id if line else False
            rec.current_ward_id = line.ward_id.id if line else False
            rec.current_category_id = line.category_id.id if line else False

    @api.depends("hospital_bed_line_id")
    def _compute_bed_line_count(self):
        for rec in self:
            rec.bed_line_count = len(rec.hospital_bed_line_id)

    def action_shift_bed(self):
        self.ensure_one()
        if self.state not in ("activated",):
            raise UserError(_("Patient must be in Admitted state to be shifted."))
        if not self.current_bed_line_id:
            raise UserError(_(
                "There is no active bed for this admission yet. "
                "Add the first bed line under the Hospital Bed Line tab."
            ))
        return {
            "name": _("Shift Bed"),
            "type": "ir.actions.act_window",
            "res_model": "hospital.bed.transfer",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_admission_id": self.id,
                "default_current_bed_line_id": self.current_bed_line_id.id,
            },
        }

    def action_view_accommodation(self):
        self.ensure_one()
        return {
            "name": _("Accommodation History"),
            "type": "ir.actions.act_window",
            "res_model": "hospital.bed.line",
            "view_mode": "list,form",
            "domain": [("hospital_bed_item_id", "=", self.id)],
            "context": {
                "default_hospital_bed_item_id": self.id,
            },
        }

    def _recompute_bed_charges(self):
        """Force a fresh recompute of bed line days/total — used by Calculate button
        so open bed lines reflect time elapsed up to 'now'."""
        for rec in self:
            lines = rec.hospital_bed_line_id
            if not lines:
                continue
            self.env.add_to_compute(lines._fields["days_count"], lines)
            self.env.add_to_compute(lines._fields["total_amount"], lines)
            lines._compute_charges()

    def calculate_bill(self):
        self._recompute_bed_charges()
        return super().calculate_bill()

    def hospital_change_status(self):
        res = super().hospital_change_status()
        for rec in self:
            for line in rec.hospital_bed_line_id.filtered(lambda l: not l.end_date and l.bed_no):
                if line.bed_no.state == "available":
                    line.bed_no.state = "occupied"
        return res

    def btn_final_settlement(self):
        res = super().btn_final_settlement()
        for rec in self:
            if rec.state == "released":
                for line in rec.hospital_bed_line_id.filtered(lambda l: not l.end_date):
                    line.end_date = fields.Datetime.now()
                    if line.bed_no and line.bed_no.state == "occupied":
                        line.bed_no.state = "available"
        return res

    def admission_cancel(self):
        res = super().admission_cancel()
        for rec in self:
            for line in rec.hospital_bed_line_id.filtered(lambda l: not l.end_date):
                line.end_date = fields.Datetime.now()
                if line.bed_no and line.bed_no.state == "occupied":
                    line.bed_no.state = "available"
        return res
