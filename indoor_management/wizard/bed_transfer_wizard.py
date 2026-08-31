from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HospitalBedTransfer(models.TransientModel):
    _name = "hospital.bed.transfer"
    _description = "Hospital Bed Transfer Wizard"

    admission_id = fields.Many2one(
        "hospital.admission", string="Admission", required=True, readonly=True,
    )
    patient_name = fields.Many2one(
        "patient.info", related="admission_id.patient_name", string="Patient", readonly=True,
    )

    current_bed_line_id = fields.Many2one(
        "hospital.bed.line", string="Current Accommodation", required=True, readonly=True,
    )
    current_bed_id = fields.Many2one(
        "hospital.bed", related="current_bed_line_id.bed_no", string="Current Bed", readonly=True,
    )
    current_ward_id = fields.Many2one(
        "hospital.ward", related="current_bed_line_id.ward_id", string="Current Ward", readonly=True,
    )
    current_category_id = fields.Many2one(
        "bed.category", related="current_bed_line_id.category_id", string="Current Category", readonly=True,
    )

    new_category_id = fields.Many2one("bed.category", string="New Category", required=True)
    new_ward_id = fields.Many2one(
        "hospital.ward", string="New Ward / Room", required=True,
        domain="[('category_id', '=', new_category_id)]",
    )
    new_bed_id = fields.Many2one(
        "hospital.bed", string="New Bed", required=True,
        # An occupied or out-of-service bed is not somewhere a patient can be
        # moved, so it is not offered. The constraint on hospital.bed.line is
        # still the real guard - this only keeps the list honest.
        domain="[('ward_id', '=', new_ward_id), ('active', '=', True), "
               "('state', 'in', ('available', 'reserved'))]",
    )
    new_bed_state = fields.Selection(related="new_bed_id.state", readonly=True)
    new_bed_warning = fields.Char(compute="_compute_new_bed_warning")

    shift_datetime = fields.Datetime(
        string="Shift Date/Time", required=True, default=fields.Datetime.now,
    )
    override_charge = fields.Float(
        string="New Bed Per-Day Charge",
        help="Defaults to the new bed's effective rate. Edit to override for this admission.",
    )
    reason = fields.Char(string="Reason", required=True)
    notes = fields.Text(string="Notes")

    @api.depends("new_bed_id")
    def _compute_new_bed_warning(self):
        for rec in self:
            if rec.new_bed_id and rec.new_bed_id.state == "reserved":
                rec.new_bed_warning = _(
                    "This bed is marked Reserved. Moving the patient in will take it."
                )
            else:
                rec.new_bed_warning = False

    @api.onchange("new_category_id")
    def _onchange_new_category(self):
        self.new_ward_id = False
        self.new_bed_id = False

    @api.onchange("new_ward_id")
    def _onchange_new_ward(self):
        self.new_bed_id = False

    @api.onchange("new_bed_id")
    def _onchange_new_bed(self):
        if self.new_bed_id:
            self.override_charge = self.new_bed_id.get_effective_charge()

    def action_confirm(self):
        self.ensure_one()
        if not self.current_bed_line_id:
            raise UserError(_("No current accommodation to shift from."))
        if self.new_bed_id == self.current_bed_id:
            raise UserError(_("New bed must be different from the current bed."))
        if self.shift_datetime < self.current_bed_line_id.start_date:
            raise UserError(_("Shift time cannot be earlier than the current bed's start time."))

        if self.new_bed_id.state == "occupied":
            occupant = self.new_bed_id.current_admission_id
            raise UserError(_(
                "Bed %(bed)s is occupied%(by)s. Release or shift that patient "
                "before moving someone into it.",
                bed=self.new_bed_id.display_name,
                by=(" by %s" % occupant.patient_name.name) if occupant.patient_name else "",
            ))
        if self.new_bed_id.state == "maintenance":
            raise UserError(_(
                "Bed %s is under maintenance.", self.new_bed_id.display_name))

        # Close the old stay first, then open the new one. Both writes sync the
        # bed status from the lines, so no status is set by hand here -- and
        # doing it in this order means the constraint sees the old bed already
        # released if the patient is being moved back into a bed they had before.
        self.current_bed_line_id.end_date = self.shift_datetime

        self.env["hospital.bed.line"].create({
            "hospital_bed_item_id": self.admission_id.id,
            "bed_no": self.new_bed_id.id,
            "start_date": self.shift_datetime,
            "bed_qty": 1,
            "perday_charge": self.override_charge or self.new_bed_id.get_effective_charge(),
            "shift_reason": self.reason,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "hospital.admission",
            "res_id": self.admission_id.id,
            "view_mode": "form",
            "target": "current",
        }
