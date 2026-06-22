from odoo import api, fields, models


class HospitalWard(models.Model):
    _name = "hospital.ward"
    _description = "Hospital Ward / Room"
    _order = "category_id, name"

    name = fields.Char(string="Ward / Room", required=True)
    code = fields.Char(string="Code")
    category_id = fields.Many2one("bed.category", string="Category", required=True, ondelete="restrict")
    floor = fields.Char(string="Floor")
    capacity = fields.Integer(string="Capacity", default=1, help="Maximum beds in this ward/room")
    perday_charge = fields.Float(
        string="Per-Day Charge",
        help="Overrides the category's default per-day charge for beds in this ward. Leave 0 to use the category default.",
    )
    notes = fields.Text(string="Notes")
    active = fields.Boolean(default=True)

    bed_ids = fields.One2many("hospital.bed", "ward_id", string="Beds")
    bed_count = fields.Integer(compute="_compute_counts")
    available_bed_count = fields.Integer(compute="_compute_counts")
    occupied_bed_count = fields.Integer(compute="_compute_counts")

    _hospital_ward_name_uniq = models.Constraint(
        "unique(name)",
        "Ward name must be unique.",
    )

    @api.depends("bed_ids", "bed_ids.state", "bed_ids.active")
    def _compute_counts(self):
        for rec in self:
            beds = rec.bed_ids.filtered(lambda b: b.active)
            rec.bed_count = len(beds)
            rec.available_bed_count = len(beds.filtered(lambda b: b.state == "available"))
            rec.occupied_bed_count = len(beds.filtered(lambda b: b.state == "occupied"))
