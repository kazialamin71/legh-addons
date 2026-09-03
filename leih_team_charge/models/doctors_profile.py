from odoo import api, fields, models

from .team_charge_mixin import SHARE_METHODS


class DoctorsProfile(models.Model):
    """Doctors need a partner before they can be owed money.

    Odoo cannot carry a payable against anything but a partner, so this mirrors
    what leih_patient already does for patient.info. It costs nothing under the
    off-ledger treatment and is what lets the hospital switch to posting the
    liability later without a migration.
    """
    _inherit = 'doctors.profile'

    partner_id = fields.Many2one(
        'res.partner', string='Accounting Contact', copy=False, readonly=True,
        help='Created automatically. What the doctor is owed is tracked against '
             'this contact.')
    default_team_method = fields.Selection(
        SHARE_METHODS, string='Default Share Basis', default='none', required=True,
        help='Fallback for items that carry no share of their own.')
    default_team_value = fields.Float('Default Share Rate')

    def _partner_vals(self):
        self.ensure_one()
        return {'name': self.name, 'company_type': 'person', 'supplier_rank': 1}

    def _ensure_partner(self):
        Partner = self.env['res.partner']
        for rec in self.filtered(lambda d: not d.partner_id and d.name):
            rec.partner_id = Partner.create(rec._partner_vals())
        return True

    @api.model_create_multi
    def create(self, vals_list):
        doctors = super().create(vals_list)
        doctors._ensure_partner()
        return doctors

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for rec in self.filtered('partner_id'):
                rec.partner_id.name = rec.name
        self._ensure_partner()
        return res
