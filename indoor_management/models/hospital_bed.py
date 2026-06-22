from odoo import api, fields, models


class HospitalBed(models.Model):
    _inherit = "hospital.bed"
    _order = "ward_id, name"

    name = fields.Char(string="Bed Number", required=True)
    code = fields.Char(string="Code")

    ward_id = fields.Many2one(
        "hospital.ward",
        string="Ward / Room",
        ondelete="restrict",
        index=True,
    )
    category_id = fields.Many2one(
        "bed.category",
        string="Category",
        related="ward_id.category_id",
        store=True,
        readonly=True,
    )
    bed_qty = fields.Integer(string="Bed Quantity", default=1)
    perday_charge = fields.Float(
        string="Per-Day Charge",
        help="If 0, falls back to ward charge, then category default.",
    )
    total_amount = fields.Float(string="Total Amount")

    state = fields.Selection(
        [
            ("available", "Available"),
            ("occupied", "Occupied"),
            ("reserved", "Reserved"),
            ("maintenance", "Under Maintenance"),
        ],
        string="Status",
        default="available",
        tracking=True,
        required=True,
    )
    current_admission_id = fields.Many2one(
        "hospital.admission",
        string="Current Patient",
        compute="_compute_current_admission",
        store=False,
    )
    notes = fields.Text(string="Notes")
    active = fields.Boolean(default=True)

    _hospital_bed_name_uniq = models.Constraint(
        "unique(name)",
        "Bed number must be unique.",
    )

    @api.depends("state")
    def _compute_current_admission(self):
        Line = self.env["hospital.bed.line"]
        for bed in self:
            line = Line.search(
                [
                    ("bed_no", "=", bed.id),
                    ("end_date", "=", False),
                    ("hospital_bed_item_id.state", "=", "activated"),
                ],
                order="start_date desc",
                limit=1,
            )
            bed.current_admission_id = line.hospital_bed_item_id.id if line else False

    def get_effective_charge(self):
        """Return the per-day charge to apply: bed > ward > category."""
        self.ensure_one()
        if self.perday_charge:
            return self.perday_charge
        if self.ward_id and self.ward_id.perday_charge:
            return self.ward_id.perday_charge
        return self.category_id.perday_charge or 0.0
