from odoo import api, fields, models


class BedCategory(models.Model):
    _name = "bed.category"
    _description = "Bed Category"
    _order = "sequence, name"

    name = fields.Char(string="Category", required=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(default=10)
    perday_charge = fields.Float(string="Default Per-Day Charge")
    charge_rule_id = fields.Many2one(
        "bed.charge.rule",
        string="Charge Rule",
        help="How hours of occupancy become a day's charge for this category. "
             "Blank follows the default rule.",
    )
    color = fields.Integer(string="Color")
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)

    ward_ids = fields.One2many("hospital.ward", "category_id", string="Wards")
    bed_ids = fields.One2many("hospital.bed", "category_id", string="Beds")

    bed_count = fields.Integer(compute="_compute_counts")
    available_bed_count = fields.Integer(compute="_compute_counts")
    occupied_bed_count = fields.Integer(compute="_compute_counts")

    _bed_category_name_uniq = models.Constraint(
        "unique(name)",
        "Category name must be unique.",
    )

    @api.depends("bed_ids", "bed_ids.state", "bed_ids.active")
    def _compute_counts(self):
        for rec in self:
            beds = rec.bed_ids.filtered(lambda b: b.active)
            rec.bed_count = len(beds)
            rec.available_bed_count = len(beds.filtered(lambda b: b.state == "available"))
            rec.occupied_bed_count = len(beds.filtered(lambda b: b.state == "occupied"))
