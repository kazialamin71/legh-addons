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
            parts = [p for p in (line.ward_id.display_name,
                                 line.category_id.display_name,
                                 line.bed_no.display_name) if p]
            rec.current_location = " / ".join(parts) if parts else ""

    current_location = fields.Char(
        string="Current Location", compute="_compute_current_bed",
        help="Where the patient is right now, as one readable line.")

    def action_open_current_bed(self):
        """Open the bed the patient is in."""
        self.ensure_one()
        if not self.current_bed_id:
            raise UserError(_("This patient has no bed assigned right now."))
        return {
            "type": "ir.actions.act_window",
            "name": self.current_bed_id.display_name,
            "res_model": "hospital.bed",
            "res_id": self.current_bed_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_current_ward(self):
        """Show the whole ward, so the desk can see what is free next door.

        The board is grouped and colour-coded by state, which is the question
        actually being asked when someone looks up where a patient is: not just
        "which bed", but "what else is free around them".
        """
        self.ensure_one()
        if not self.current_ward_id:
            raise UserError(_("This patient is not in a ward right now."))
        return {
            "type": "ir.actions.act_window",
            "name": self.current_ward_id.display_name,
            "res_model": "hospital.bed",
            "view_mode": "kanban,list,form",
            "domain": [("ward_id", "=", self.current_ward_id.id)],
            "context": {"search_default_group_category": 1},
            "target": "current",
        }

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

    def _close_open_bed_lines(self):
        """End every open stay and hand the beds back.

        Closing the line is all that is needed: hospital.bed.line.write syncs the
        bed's status from its lines, so the bed is freed whatever state it was
        sitting in. The old code only freed a bed that happened to read
        'occupied', which meant a bed left 'reserved' -- or one whose status had
        drifted -- stayed blocked after the patient went home.
        """
        now = fields.Datetime.now()
        for rec in self:
            for line in rec.hospital_bed_line_id.filtered(lambda l: not l.end_date):
                # Never end a stay before it started: cancelling an admission
                # whose bed line is future-dated would otherwise leave a
                # negative-length interval behind.
                line.end_date = max(now, line.start_date) if line.start_date else now

    def hospital_change_status(self):
        res = super().hospital_change_status()
        # Confirming turns held beds into occupied ones.
        self.mapped("hospital_bed_line_id.bed_no")._sync_state()
        return res

    def btn_final_settlement(self):
        res = super().btn_final_settlement()
        self.filtered(lambda r: r.state == "released")._close_open_bed_lines()
        return res

    def admission_cancel(self):
        res = super().admission_cancel()
        self._close_open_bed_lines()
        return res
