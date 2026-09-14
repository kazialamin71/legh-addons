from odoo import api, fields, models


class AdmissionChargeItem(models.Model):
    """Charge type comes from ``admission.charge.type`` instead of a hard-coded
    list. Same column, same stored codes -- only the list of choices moved."""
    _inherit = 'admission.charge.item'

    charge_type = fields.Selection(
        selection=lambda self: self.env['admission.charge.type']._selection())

    @api.depends('name', 'charge_type')
    def _compute_display_name(self):
        labels = dict(self.env['admission.charge.type']._selection())
        for rec in self:
            label = labels.get(rec.charge_type)
            rec.display_name = f'[{label}] {rec.name}' if label and rec.name else (rec.name or '')
