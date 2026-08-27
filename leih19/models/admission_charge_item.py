from odoo import api, fields, models

# Shared by the catalogue and the admission lines that consume it, and mapped
# 1:1 onto hospital.admission.charge.service_type by leih_admission.
CHARGE_TYPES = [
    ("admission", "Admission Charge"),
    ("icu", "ICU"),
    ("nicu", "NICU"),
    ("other", "Other Charge"),
]


class AdmissionChargeItem(models.Model):
    """Catalogue of non-diagnostic admission charges.

    Admission / ICU / NICU / other ward charges used to be created as
    ``examination.entry`` records, which dragged them into the lab catalogue
    (sample collection, results, report layouts...). They live here instead, so
    ``examination.entry`` stays a catalogue of diagnostic tests and services.
    """
    _name = "admission.charge.item"
    _description = "Admission Charge Item"
    _order = "charge_type, name"

    name = fields.Char(string="Charge Name", required=True)
    charge_type = fields.Selection(
        CHARGE_TYPES, string="Charge Type", required=True, default="admission",
        help="Bucket this item is billed under on the admission statement.")
    rate = fields.Float(string="Rate", help="Default price proposed on the admission line.")
    department = fields.Many2one(
        "diagnosis.department", string="Income Unit",
        help="Cost-center the income is attributed to (e.g. ICU, NICU).")
    accounts_id = fields.Many2one("account.account", string="Account ID")
    note = fields.Char(string="Note")
    active = fields.Boolean(default=True)

    @api.model
    def _from_examination_entry(self, entry):
        """Catalogue item mirroring an examination.entry, created on demand.

        Examination packages are still built out of examination.entry records,
        so expanding one onto an admission needs a matching charge item to link
        the line to. Matched by name, created once, reused afterwards."""
        if not entry:
            return self.browse()
        item = self.with_context(active_test=False).search(
            [("name", "=", entry.name)], limit=1)
        if not item:
            item = self.create({
                "name": entry.name,
                "charge_type": "other",
                "rate": entry.rate,
                "department": entry.department.id if entry.department else False,
                "accounts_id": entry.accounts_id.id if entry.accounts_id else False,
            })
        return item

    @api.depends("name", "charge_type")
    def _compute_display_name(self):
        labels = dict(CHARGE_TYPES)
        for rec in self:
            label = labels.get(rec.charge_type)
            rec.display_name = f"[{label}] {rec.name}" if label and rec.name else (rec.name or "")
