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

    # A many2one dropdown renders display_name and nothing else -- no per-row
    # decoration reaches it -- so the status travels inside the name. A coloured
    # disc is legible at a glance in the list someone is picking a bed from,
    # which is the moment it matters.
    _STATE_MARK = {
        "available": "\U0001F7E2",    # green
        "occupied": "\U0001F534",     # red
        "reserved": "\U0001F7E1",     # amber
        "maintenance": "\u26AB",      # grey
    }

    @api.depends("name", "state", "ward_id")
    def _compute_display_name(self):
        for bed in self:
            mark = self._STATE_MARK.get(bed.state, "")
            ward = bed.ward_id.name if bed.ward_id else ""
            label = "%s / %s" % (ward, bed.name) if ward else (bed.name or "")
            bed.display_name = ("%s %s" % (mark, label)).strip()

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

    def _sync_state(self):
        """Derive availability from the accommodation lines that reference this bed.

        The status used to be nudged by hand in five different places, each
        guarded with ``if bed.state == 'occupied'``. Any drift -- a bed line added
        straight on the admission's Bed tab, a bed left 'reserved', a release that
        ran while the state said something unexpected -- and the guard silently
        did nothing, so beds stayed occupied forever or were freed while a patient
        was still in them. Occupancy is a fact about the bed lines, so it is read
        from them rather than tracked separately.

        'maintenance' is the one sticky state: a bed out for repair is a decision
        about the bed itself, so occupancy never clears it (and the shift wizard
        refuses to move anyone into one).

        Everything else is derived. 'reserved' is NOT preserved here, because
        this only ever runs for beds a stay was just opened or closed on -- and a
        hold that someone has been lying in is a hold already spent. Leaving it
        reserved would keep the bed blocked after the patient went home, which is
        the exact bug this is meant to end. A genuinely reserved empty bed is
        never passed through here, so its hold survives untouched.
        """
        Line = self.env['hospital.bed.line']
        for bed in self:
            if bed.state == 'maintenance':
                continue
            occupied = Line.search_count([
                ('bed_no', '=', bed.id),
                ('end_date', '=', False),
                ('hospital_bed_item_id.state', 'not in', ('cancelled', 'released')),
            ])
            new_state = 'occupied' if occupied else 'available'
            if bed.state != new_state:
                bed.state = new_state

    def get_effective_charge(self):
        """Return the per-day charge to apply: bed > ward > category."""
        self.ensure_one()
        if self.perday_charge:
            return self.perday_charge
        if self.ward_id and self.ward_id.perday_charge:
            return self.ward_id.perday_charge
        return self.category_id.perday_charge or 0.0
